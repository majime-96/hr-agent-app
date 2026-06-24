import os
import re
import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic

st.set_page_config(
    page_title="HR Agent | 課題診断",
    page_icon="🌱",
    layout="centered",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 760px; }
    .hr-header { text-align: center; margin-bottom: 0.5rem; }
    .hr-header h2 { font-size: 1.6rem; font-weight: 700; margin-bottom: 0; }
    .hr-header p  { color: #666; font-size: 0.9rem; margin-top: 0.2rem; }
    .stChatMessage hr { margin: 0.8rem 0; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# システムプロンプト（外部ファイルから読み込み）
# ============================================================
@st.cache_resource
def load_system_prompt():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_path = os.path.join(base_dir, "HR_Agent_SystemPrompt.md")
    archetypes_path = os.path.join(base_dir, "SystemArchetypes_Knowledge.md")
    with open(main_path, "r", encoding="utf-8") as f:
        main_prompt = f.read()
    with open(archetypes_path, "r", encoding="utf-8") as f:
        archetypes = f.read()
    return (
        main_prompt
        + "\n\n---\n\n"
        + "# 参照ナレッジ：システム原型（ステップ4で参照）\n\n"
        + archetypes
    )

SYSTEM_PROMPT = load_system_prompt()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192

# ============================================================
# Anthropic クライアント
# ============================================================
@st.cache_resource
def get_client():
    return Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# ============================================================
# HTMLコードブロックを検出して適切にレンダリング
# ============================================================

# html・HTML・Htmlなど大文字小文字を問わず、閉じタグ欠落にも対応
HTML_BLOCK = re.compile(r'```[Hh][Tt][Mm][Ll]?\s*\n(.*?)(?:```|$)', re.DOTALL)

def format_choices(text):
    """a. xxx　b. xxx のようにインライン化された選択肢を改行する。"""
    return re.sub(r'([^\n])[　\s]+([a-f]\.\s)', r'\1\n\n\2', text)

def render_content(content):
    last_end = 0
    has_match = False
    for match in HTML_BLOCK.finditer(content):
        has_match = True
        before = content[last_end:match.start()].strip()
        if before:
            st.markdown(format_choices(before), unsafe_allow_html=True)
        html_content = match.group(1).strip()
        if html_content:
            components.html(html_content, height=800, scrolling=True)
        last_end = match.end()
    if has_match:
        after = content[last_end:].strip()
        if after:
            st.markdown(format_choices(after), unsafe_allow_html=True)
    else:
        st.markdown(format_choices(content), unsafe_allow_html=True)

# ============================================================
# 初期メッセージ
# ============================================================
INITIAL_MESSAGE = """\
こんにちは。Racoosaは、組織をひとりで支える方が「孤独な意思決定から解放され、やりたい未来をつくる仕事に集中できる状態」にするためのエージェントを開発しています。
ここで一緒に、社内の人事・組織に関して気になっていること、頭の中にあることを、見える形にしていきましょうか。
整理できたことには、対面のセッションをお待ちしています。今日は、その準備のようなものなので、気楽にどうぞ。思いつくままに言っていただいて大丈夫です。

---

今日は、5つのステップで、気になっていることを整理して、最後に図にまとめていきます。

ステップ1：人事・組織について気になっていることを開く

ステップ2：気になっていることの全体を図にして確認する

ステップ3：課題同士のつながりを一緒に探る

ステップ4：課題の奥にどんなことがあるか、仮説を図にまとめる

ステップ5：対面で話したいことを見つける

まずは、ステップ1からはじめましょうか。

---

はじめに、本題に進む前に、進め方を少しお伺いしたいです。3つだけお伺いします。選んでいただいても自由に書いていただいても大丈夫です。

① 相づち・承認はどのくらいほしいですか？

a. しっかり（例：「なるほど」「それは大事な観点ですね」な感じ）

b. 控えめ（例：「わかりました」程度で、話し合いに進もう）

c. いらない
"""

# ============================================================
# セッション初期化
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": INITIAL_MESSAGE}
    ]

# ============================================================
# UI
# ============================================================
st.markdown(
    '<div class="hr-header"><h2>🌱 HR Agent</h2>'
    '<p>ひとり人事・COOのための課題診断</p></div>',
    unsafe_allow_html=True,
)
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_content(msg["content"])
        else:
            st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("思いつくままに話してください..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client = get_client()
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_reply = ""
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=st.session_state.messages,
        ) as stream:
            for text in stream.text_stream:
                full_reply += text
                placeholder.markdown(full_reply + "▌", unsafe_allow_html=True)
        placeholder.empty()
        render_content(full_reply)

    st.session_state.messages.append({"role": "assistant", "content": full_reply})
