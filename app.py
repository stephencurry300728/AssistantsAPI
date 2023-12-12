# 导入必要的库
import openai
import streamlit as st
from dotenv import load_dotenv
import os
import time

# 设置代理（如果需要）
os.environ["http_proxy"] = "http://localhost:7890"
os.environ["https_proxy"] = "http://localhost:7890"

# 读取环境变量 "OPENAI_API_KEY"
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# 初始化 OpenAI 的客户端
client = openai.OpenAI(api_key=openai_api_key)
# 调用在网页UI创建好的assistant
assistant = client.beta.assistants.retrieve("asst_whC9OsPCQgoDlpPDvT7xosyG") # 硬编码调用已经创建好的assistant

# 检查是否已经创建了一个线程
if "thread_id" not in st.session_state:
    # 创建一个新的线程
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id # 将新线程的 ID 存储在会话状态中
else:
    # 使用现有的线程 ID
    thread_id = st.session_state.thread_id

# 设置 Streamlit 页面的标题和图标
st.set_page_config(page_title="ChatGPT", page_icon=":speech_balloon:")

# 文件上传逻辑
def upload_to_openai(filepath):
    """Upload a file to OpenAI and return its file ID."""
    with open(filepath, "rb") as file:
        response = openai.files.create(file=file.read(), purpose="assistants")
    return response.id

# 侧边栏文件上传选项
uploaded_file = st.sidebar.file_uploader("Upload a file to OpenAI embeddings", key="file_uploader")

if st.sidebar.button("Upload File"):
    if uploaded_file:
        with open(f"{uploaded_file.name}", "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_id = upload_to_openai(f"{uploaded_file.name}")
        st.sidebar.write(f"Uploaded File ID: {file_id}")

# 主聊天界面设置
st.title("OpenAI Assistants API Chat")
st.write("Thread ID: ", st.session_state.thread_id)

# 初始化消息列表
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示现有聊天消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 聊天输入
if prompt := st.chat_input("Message ChatGPT..."):
    # 添加用户消息并显示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 将用户消息添加到线程
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    # 创建运行并添加附加指令
    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant.id,
    )

    # 等待运行完成并获取助手的消息
    while run.status != 'completed':
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id,
            run_id=run.id
        )

    # 检索由助手添加的消息
    messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id
    )

    # 处理并显示助手的消息
    assistant_messages_for_run = [
        message for message in messages.data 
        if message.run_id == run.id and message.role == "assistant"
    ]
    for message in assistant_messages_for_run:
        new_message = message.content[0].text.value
        # 处理带有citations的消息
        # new_message = process_message_with_citations(message) 
        st.session_state.messages.append({"role": "assistant", "content": new_message})
        with st.chat_message("assistant"):
            st.markdown(new_message, unsafe_allow_html=True)

# def process_message_with_citations(message):
#     """Extract content and annotations from the message and format citations as footnotes."""
#     message_content = message.content[0].text
#     annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
#     citations = []

#     # Iterate over the annotations and add footnotes
#     for index, annotation in enumerate(annotations):
#         # Replace the text with a footnote
#         message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

#         # Gather citations based on annotation attributes
#         if (file_citation := getattr(annotation, 'file_citation', None)):
#             # Retrieve the cited file details (dummy response here since we can't call OpenAI)
#             cited_file = {'filename': 'cited_document.pdf'}  # This should be replaced with actual file retrieval
#             citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
#         elif (file_path := getattr(annotation, 'file_path', None)):
#             # Placeholder for file download citation
#             cited_file = {'filename': 'downloaded_document.pdf'}  # This should be replaced with actual file retrieval
#             citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')  # The download link should be replaced with the actual download path

#     # Add footnotes to the end of the message content
#     full_response = message_content.value + '\n\n' + '\n'.join(citations)
#     return full_response