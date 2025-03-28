from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from src.config.config import (
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS,
    TIME_RELATED_KEYWORDS
)
from src.utils.time_utils import get_current_time, format_date, format_time

class ChatHandler:
    def __init__(self, retriever):
        self.llm = ChatOpenAI(
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=retriever
        )

    def is_time_related_question(self, prompt):
        prompt_lower = prompt.lower()
        is_date_question = any(keyword in prompt_lower for keyword in TIME_RELATED_KEYWORDS["date"])
        is_time_question = any(keyword in prompt_lower for keyword in TIME_RELATED_KEYWORDS["time"])
        return is_date_question, is_time_question

    def handle_time_question(self, is_date_question, is_time_question):
        current_time = get_current_time()
        if is_date_question:
            return format_date(current_time)
        else:
            return format_time(current_time)

    def handle_query(self, prompt):
        is_date_question, is_time_question = self.is_time_related_question(prompt)
        
        if is_date_question or is_time_question:
            return self.handle_time_question(is_date_question, is_time_question)
        else:
            try:
                return self.qa_chain.run(prompt)
            except Exception as e:
                return f"Tôi xin lỗi, nhưng tôi gặp lỗi khi tìm kiếm thông tin: {str(e)}" 