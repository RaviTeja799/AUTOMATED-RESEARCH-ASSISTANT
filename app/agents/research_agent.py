"""
Research assistant agent with LangChain.
Compatible with LangChain 1.x / langchain-classic.
"""
from typing import List, Dict, Any, Optional
import asyncio

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

from app.agents.tools import (
    SearchPapersTool,
    AnswerQuestionTool,
    SummarizePaperTool,
    ComparePapersTool,
    GenerateLiteratureReviewTool
)
from app.core.config import settings
from app.utils.logger import app_logger


class ResearchAgent:
    """
    Research assistant agent with tool orchestration and memory.
    """

    def __init__(
        self,
        query_service,
        summarization_service,
        literature_service,
        retriever,
    ):
        self.query_service = query_service
        self.summarization_service = summarization_service
        self.literature_service = literature_service
        self.retriever = retriever

        # Initialize LLM
        self.llm = Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.7,
        )

        # Initialize tools
        self.tools = self._initialize_tools()

        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )

        # Create agent and executor
        self.agent_executor = self._create_executor()

        app_logger.info("ResearchAgent initialized")

    def _initialize_tools(self) -> List:
        return [
            SearchPapersTool(retriever=self.retriever),
            AnswerQuestionTool(query_service=self.query_service),
            SummarizePaperTool(summarization_service=self.summarization_service),
            ComparePapersTool(query_service=self.query_service),
            GenerateLiteratureReviewTool(literature_service=self.literature_service)
        ]

    def _create_executor(self) -> AgentExecutor:
        template = """You are a research assistant agent with access to tools for analyzing academic papers.

TOOLS:
{tools}

TOOL NAMES: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Previous conversation:
{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "chat_history", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join([f"{t.name}: {t.description}" for t in self.tools]),
                "tool_names": ", ".join([t.name for t in self.tools])
            }
        )

        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=settings.agent_verbose,
            max_iterations=settings.agent_max_iterations,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

    async def process_query(self, query: str) -> Dict[str, Any]:
        app_logger.info(f"Agent processing: {query[:100]}...")
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent_executor.invoke({"input": query})
            )
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            app_logger.error(f"Agent error: {e}", exc_info=True)
            return {
                "output": f"Error processing request: {str(e)}",
                "intermediate_steps": [],
            }

    def clear_memory(self):
        self.memory.clear()

    def get_memory(self) -> List:
        return self.memory.chat_memory.messages


class IntentClassifier:
    INTENTS = {
        "SEARCH": ["find", "search", "look for", "papers on", "research on"],
        "QUESTION": ["what", "how", "why", "when", "explain", "describe"],
        "SUMMARIZE": ["summarize", "summary", "overview of paper", "tell me about paper"],
        "COMPARE": ["compare", "difference", "versus", "vs", "contrast"],
        "LITERATURE_REVIEW": ["literature review", "state of the art", "survey", "comprehensive overview"]
    }

    @staticmethod
    def classify(query: str) -> str:
        query_lower = query.lower()
        for intent, keywords in IntentClassifier.INTENTS.items():
            if any(kw in query_lower for kw in keywords):
                return intent
        return "QUESTION"


class AgentOrchestrator:
    def __init__(self, research_agent: ResearchAgent):
        self.agent = research_agent
        self.intent_classifier = IntentClassifier()
        app_logger.info("AgentOrchestrator initialized")

    async def process(self, query: str, use_intent_routing: bool = True) -> Dict[str, Any]:
        intent = self.intent_classifier.classify(query) if use_intent_routing else "GENERAL"
        app_logger.info(f"Intent: {intent}")

        enhanced_query = f"[Intent: {intent}] {query}" if use_intent_routing else query
        result = await self.agent.process_query(enhanced_query)
        result["intent"] = intent
        return result

    def clear_memory(self):
        self.agent.clear_memory()

    def get_conversation_history(self) -> List:
        return self.agent.get_memory()


__all__ = ["ResearchAgent", "IntentClassifier", "AgentOrchestrator"]
