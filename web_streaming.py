import streamlit as st
import atexit
import asyncio
from my_agent import MyAgent

# Configure the page
st.set_page_config(
    page_title="streaming",
    layout="wide"
)

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Add title on the page
st.title("데모 제목입니다.")
st.write("데모 설명 페이지입니다.")

# Initialize the agent once
if "my_agent_instance" not in st.session_state:
    st.session_state.my_agent_instance = MyAgent()
    st.session_state.agent = st.session_state.my_agent_instance.initialize_mcp()
    atexit.register(st.session_state.my_agent_instance.cleanup)

# Display old chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.empty()
        if message.get("type") == "tool_use":
            with st.expander("🛠️ Using Tool...", expanded=False):
                st.code(message["content"])
        elif message.get("type") == "reasoning":
            with st.expander("🧠 Reasoning...", expanded=False):
                st.markdown(message["content"])
        else:
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask your agent..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Clear previous tool usage details
    if "details_placeholder" in st.session_state:
        st.session_state.details_placeholder.empty()

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare containers for response
    with st.chat_message("assistant"):
        st.session_state.details_placeholder = st.empty()

    # 스트리밍 처리 함수
    async def process_stream():
        output = []
        tool_use_ids = set()
        
        async for event in st.session_state.agent.stream_async(prompt):
            with st.session_state.details_placeholder.container():
                if "data" in event:
                    if not output or output[-1]["type"] != "data":
                        output.append({"type": "data", "content": event["data"]})
                    else:
                        output[-1]["content"] += event["data"]
                elif "current_tool_use" in event and event["current_tool_use"].get("name"):
                    tool_use_id = event["current_tool_use"].get("toolUseId")
                    tool_name = event["current_tool_use"]["name"]
                    tool_input = str(event["current_tool_use"]["input"])
                    
                    # 기존 도구 찾기
                    existing_tool = None
                    for i, item in enumerate(output):
                        if item["type"] == "tool_use" and item.get("id") == tool_use_id:
                            existing_tool = i
                            break
                    
                    if existing_tool is not None:
                        # 기존 도구 업데이트
                        output[existing_tool]["content"] = f"{tool_name} with args: {tool_input}"
                    elif tool_use_id not in tool_use_ids:
                        # 새 도구 추가
                        output.append({"type": "tool_use", "content": f"{tool_name} with args: {tool_input}", "id": tool_use_id})
                        tool_use_ids.add(tool_use_id)
                elif "reasoningText" in event:
                    if not output or output[-1]["type"] != "reasoning":
                        output.append({"type": "reasoning", "content": event["reasoningText"]})
                    else:
                        output[-1]["content"] += event["reasoningText"]

                # 실시간 표시
                for item in output:
                    if item["type"] == "data":
                        st.markdown(item["content"])
                    elif item["type"] == "tool_use":
                        with st.expander("🛠️ Using Tool...", expanded=True):
                            st.code(item["content"])
                    elif item["type"] == "reasoning":
                        with st.expander("🧠 Reasoning...", expanded=True):
                            st.markdown(item["content"])
        return output

    # 실행
    st.session_state.output = asyncio.run(process_stream())

    # Add assistant messages to chat history
    for output_item in st.session_state.output:
        st.session_state.messages.append({"role": "assistant", "type": output_item["type"], "content": output_item["content"]})
