import json
from sqlalchemy.orm import Session
from config.settings import settings
from utils.llm_utils import llm_client

from api.services.files_service import (
    search_files_content_hybrid,
    search_files_by_embedded_content,
    get_files_for_user,
    get_file_by_id
)
from db.models import UserRecord, FileContentRecord, MessageRecord

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_my_user_info",
            "description": "Retrieves information about the current user you are talking to. Use this when the user greets you or asks who they are.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_files",
            "description": "Returns a list of all files uploaded by the user.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_metadata",
            "description": "Retrieves technical details such as size, type, and date about a specific file specified by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "integer", "description": "The ID of the file"}
                },
                "required": ["file_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_size_of_files",
            "description": "Retrieves and calculates the total size for all files and you have to transform it in MB",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_file",
            "description": "Summarizes the content of a file specified by its ID. Use this when the user asks for a summary or what a document is about.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "integer", "description": "The ID of the file to summarize"}
                },
                "required": ["file_id"],
            },
        },
    }
]

def tool_get_my_user_info(user_id: int, db: Session) -> str:
    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if user:
        email = getattr(user, 'email', 'Unknown')
        return f"The current user has the ID {user.id}. Email: {email}."
    return "Error: Could not retrieve user data."

def tool_list_my_files(user_id: int, db: Session) -> str:
    files = get_files_for_user(user_id, db)
    if not files:
        return "The user has no uploaded files."
    
    file_list = [f"- {f.original_file_name} (ID: {f.id})" for f in files]
    return "User's files:\n" + "\n".join(file_list)

def tool_get_file_metadata(file_id: int, user_id: int, db: Session) -> str:
    f_record = get_file_by_id(file_id, user_id, db)
    if f_record:
        return f"File Details [ID: {f_record.id}]: Name={f_record.original_file_name}, Size={f_record.size} bytes, Type={f_record.content_type}."
    return f"Error: File with ID {file_id} was not found."

def tool_get_total_size_of_files(user_id: int, db: Session):
    files = get_files_for_user(user_id, db)
    if not files:
        return "The user has no uploaded files."
    
    total_size = sum(file.size for file in files if file.size)

    return f"User's total files size is {total_size} bytes"

def tool_summarize_file(file_id: int, user_id: int, db: Session) -> str:
    f_record = get_file_by_id(file_id, user_id, db)
    if not f_record:
        return f"Error: File with ID {file_id} was not found in your account."
    
    chunks = db.query(FileContentRecord.chunk_content).filter(FileContentRecord.file_id == file_id).all()
    
    if not chunks:
        return f"The file '{f_record.original_file_name}' is empty or could not be read as text."
    
    extracted_text = "\n".join([c[0] for c in chunks[:15]])
    
    return (
        f"Here is the content of the file '{f_record.original_file_name}'. "
        f"Please write a detailed and clear summary for it:\n\n{extracted_text}"
    )

def format_search_results(search_results):
    if not search_results:
        return "No relevant information found in the documents for this query.", []
    
    context_parts = []
    sources = []
    for res in search_results:
        source_name = res["file"]["original_name"]
        text = res.get("best_chunk", "")
        context_parts.append(f"--- Source: {source_name} ---\n{text}")
        
        sources.append({
            "file_name": source_name,
            "file_id": res["file"]["id"],
            "relevance_score": float(res.get("rank", 0.0) or res.get("score", 0.0)),
            "text_snippet": text 
        })
    return "\n\n".join(context_parts), sources

def get_answer_from_agent(user_query: str, user_id: int, db: Session):
    messages = [
        {
            "role": "system", 
            "content": (
                "You are a smart and friendly assistant. "
                "You have tools available to read the user's database. "
                "Call the necessary tools to answer accurately. "
                "When providing information from files, always cite the source file name."
            )
        }
    ]
    past_messages = (
        db.query(MessageRecord)
        .filter(MessageRecord.user_id == user_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(6)
        .all()
    )

    past_messages.reverse()

    for msg in past_messages:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_query})
    
    new_user_msg = MessageRecord(user_id=user_id, role="user", content=user_query)
    db.add(new_user_msg)
    db.commit()

    response = llm_client.chat.completions.create(
        model="openai/gpt-oss-120b", 
        messages=messages,
        tools=tools_definition,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    sources_for_response = []
    print(messages)
    if tool_calls:
        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            
            args = {}
            if tool_call.function.arguments:
                args = json.loads(tool_call.function.arguments)

            function_result = ""

            if function_name == "get_my_user_info":
                function_result = tool_get_my_user_info(user_id, db)
                
            elif function_name == "list_my_files":
                function_result = tool_list_my_files(user_id, db)
                
            elif function_name == "get_file_metadata":
                function_result = tool_get_file_metadata(args.get("file_id"), user_id, db)

            elif function_name == "get_total_size_of_files":
                function_result = tool_get_total_size_of_files(user_id,db)

            elif function_name == "summarize_file":
                function_result = tool_summarize_file(args.get("file_id"), user_id, db)
                f_record = get_file_by_id(args.get("file_id"), user_id, db)
                if f_record:
                     sources_for_response.append({
                         "file_name": f_record.original_file_name,
                         "file_id": f_record.id,
                         "relevance_score": 1.0,
                         "text_snippet": "Full or partial file summarized."
                     })
                
            else:
                function_result = f"Error: Function {function_name} does not exist."

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_result,
            })

        final_response = llm_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=tools_definition
        )
        answer = final_response.choices[0].message.content

    else:
        answer = response_message.content

    new_ai_msg = MessageRecord(user_id=user_id, role="assistant", content=answer)
    db.add(new_ai_msg)
    db.commit()

    return answer, sources_for_response