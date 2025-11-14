#!/usr/bin/env python3
"""
ChatEngine - OpenAI GPT integration with streaming and function calling
"""

import json
from typing import Optional, Dict, Any, List, Iterator, Callable
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from .config import Settings, calculate_cost
from .conversation import ConversationManager


class ChatEngine:
    """Main chat engine with OpenAI GPT integration"""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        conversation: Optional[ConversationManager] = None,
    ):
        from .config import get_settings

        self.settings = settings or get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)

        # Initialize conversation manager
        if conversation:
            self.conversation = conversation
        else:
            self.conversation = ConversationManager(
                model=self.settings.model_name,
                max_tokens=self.settings.max_tokens,
            )

        # Tool registry (will be set by tool system)
        self.tools: List[Dict[str, Any]] = []
        self.tool_executor: Optional[Callable] = None
        
        # Tool call recursion tracking
        self.tool_call_depth = 0
        self.max_tool_call_depth = 5  # Prevent infinite recursion

        # Statistics
        self.stats = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "tool_calls_made": 0,
        }

    def register_tools(self, tools: List[Dict[str, Any]], executor: Callable):
        """Register tools for function calling"""
        self.tools = tools
        self.tool_executor = executor

    def chat(
        self,
        message: str,
        model: Optional[str] = None,
        stream: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Iterator[str]:
        """Send a chat message and get response

        Returns:
            Iterator[str] that yields response chunks (single chunk if not streaming)
        """

        # Add user message to conversation
        self.conversation.add_message(role="user", content=message)

        # Use defaults from settings
        model = model or self.settings.model_name
        stream = stream if stream is not None else self.settings.stream_responses
        max_tokens = max_tokens or self.settings.max_tokens
        temperature = temperature if temperature is not None else self.settings.temperature

        # Check if streaming
        if stream:
            # Streaming response - return generator
            return self._chat_generator(model, max_tokens, temperature)
        else:
            # Non-streaming response - wrap in single-yield generator for API consistency
            return self._chat_single_response(model, max_tokens, temperature)

    def _chat_single_response(self, model: str, max_tokens: int, temperature: float) -> Iterator[str]:
        """Generator for non-streaming responses (yields once)"""
        response, tool_calls_handled = self._chat_completion(model, max_tokens, temperature)

        # Add assistant response only if tools weren't used
        # Tool handling adds its own messages to the conversation
        if not tool_calls_handled and response:
            self.conversation.add_message(role="assistant", content=response)

        yield response

    def _chat_generator(self, model: str, max_tokens: int, temperature: float) -> Iterator[str]:
        """Generator for streaming responses"""
        full_response = ""
        had_tool_calls = False

        for chunk, is_tool_response in self._chat_stream(model, max_tokens, temperature):
            full_response += chunk
            had_tool_calls = is_tool_response
            yield chunk

        # Add assistant response only if tools weren't used
        # Tool handling adds its own messages to the conversation
        if not had_tool_calls and full_response:
            self.conversation.add_message(role="assistant", content=full_response)

    def _chat_completion(
        self, model: str, max_tokens: int, temperature: float
    ) -> tuple[str, bool]:
        """
        Get non-streaming chat completion

        Returns:
            tuple[str, bool]: (response_content, tool_calls_handled)
        """

        messages = self.conversation.get_messages()

        # Reasoning models (o1, o3 series) have different parameter requirements
        reasoning_models = ["o1-preview", "o1-mini", "o3", "o3-mini"]
        is_reasoning_model = any(model.startswith(rm) for rm in reasoning_models)

        # Prepare API call parameters
        params = {
            "model": model,
            "messages": messages,
        }

        # Reasoning models don't support temperature parameter
        if not is_reasoning_model:
            params["temperature"] = temperature

        # Reasoning models use max_completion_tokens instead of max_tokens
        if is_reasoning_model:
            params["max_completion_tokens"] = max_tokens
        else:
            params["max_tokens"] = max_tokens

        # Add tools if available and enabled
        if self.tools and self.settings.enable_tools:
            params["tools"] = self.tools
            params["parallel_tool_calls"] = self.settings.parallel_tool_calls

        # Make API call
        self.stats["total_requests"] += 1

        response: ChatCompletion = self.client.chat.completions.create(**params)

        # Update statistics
        if response.usage:
            self.stats["total_input_tokens"] += response.usage.prompt_tokens
            self.stats["total_output_tokens"] += response.usage.completion_tokens

            # Calculate cost
            cost = calculate_cost(
                model,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            self.stats["total_cost"] += cost

        # Handle function calling
        message = response.choices[0].message

        if message.tool_calls:
            tool_response = self._handle_tool_calls(message.tool_calls, model, max_tokens, temperature)
            return tool_response, True  # Tool calls were handled

        return message.content or "", False  # No tool calls

    def _chat_stream(
        self, model: str, max_tokens: int, temperature: float
    ) -> Iterator[tuple[str, bool]]:
        """
        Get streaming chat completion

        Yields:
            tuple[str, bool]: (chunk_content, is_tool_response)
        """

        messages = self.conversation.get_messages()

        # Reasoning models (o1, o3 series) have different parameter requirements
        reasoning_models = ["o1-preview", "o1-mini", "o3", "o3-mini"]
        is_reasoning_model = any(model.startswith(rm) for rm in reasoning_models)

        # Prepare API call parameters
        params = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        # Reasoning models don't support temperature parameter
        if not is_reasoning_model:
            params["temperature"] = temperature

        # Reasoning models use max_completion_tokens instead of max_tokens
        if is_reasoning_model:
            params["max_completion_tokens"] = max_tokens
        else:
            params["max_tokens"] = max_tokens

        # Add tools if available and enabled
        if self.tools and self.settings.enable_tools:
            params["tools"] = self.tools
            params["parallel_tool_calls"] = self.settings.parallel_tool_calls

        # Make API call
        self.stats["total_requests"] += 1

        stream = self.client.chat.completions.create(**params)

        # Collect streamed response
        full_content = ""
        tool_calls = []

        for chunk in stream:
            chunk: ChatCompletionChunk

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle content
            if delta.content:
                content_chunk = delta.content
                full_content += content_chunk
                yield content_chunk, False

            # Handle tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    # Build up tool calls incrementally
                    if tc.index >= len(tool_calls):
                        tool_calls.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        })

                    if tc.function.name:
                        tool_calls[tc.index]["function"]["name"] = tc.function.name

                    if tc.function.arguments:
                        tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

        # Handle tool calls if present
        if tool_calls:
            # Convert to proper format
            formatted_tool_calls = []
            for tc in tool_calls:
                formatted_tool_calls.append(
                    ChatCompletionMessageToolCall(
                        id=tc["id"],
                        type=tc["type"],
                        function={
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"]
                        }
                    )
                )

            # Process tool calls
            tool_response = self._handle_tool_calls(
                formatted_tool_calls, model, max_tokens, temperature
            )

            yield "\n\n" + tool_response, True

    def _handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Handle function calling"""

        if not self.tool_executor:
            return "Error: Tool executor not configured"

        # Check recursion depth to prevent infinite loops
        self.tool_call_depth += 1
        if self.tool_call_depth > self.max_tool_call_depth:
            self.tool_call_depth -= 1
            return f"Error: Maximum tool call depth ({self.max_tool_call_depth}) exceeded. Stopping to prevent infinite recursion."

        # Use try/finally to ensure recursion depth is always decremented
        try:
            self.stats["tool_calls_made"] += len(tool_calls)

            # Add assistant message with tool calls
            self.conversation.add_message(
                role="assistant",
                content=None,
                tool_calls=[tc.model_dump() for tc in tool_calls],
            )

            # Execute each tool call
            tool_results = []

            for tool_call in tool_calls:
                function_name = tool_call.function.name

                # Parse function arguments with error handling
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    error_msg = f"Error parsing tool arguments: {str(e)}"
                    self.conversation.add_message(
                        role="tool",
                        content=json.dumps({"error": error_msg}),
                        tool_call_id=tool_call.id,
                        name=function_name,
                    )
                    tool_results.append({"error": error_msg})
                    continue

                # Execute tool
                result = self.tool_executor(function_name, function_args)

                # Add tool response to conversation
                self.conversation.add_message(
                    role="tool",
                    content=json.dumps(result),
                    tool_call_id=tool_call.id,
                    name=function_name,
                )

                tool_results.append(result)

            # Get final response from model
            messages = self.conversation.get_messages()

            # Reasoning models (o1, o3 series) have different parameter requirements
            reasoning_models = ["o1-preview", "o1-mini", "o3", "o3-mini"]
            is_reasoning_model = any(model.startswith(rm) for rm in reasoning_models)

            # Prepare params for tool call response
            tool_params = {
                "model": model,
                "messages": messages,
            }

            # Reasoning models don't support temperature parameter
            if not is_reasoning_model:
                tool_params["temperature"] = temperature

            # Reasoning models use max_completion_tokens instead of max_tokens
            if is_reasoning_model:
                tool_params["max_completion_tokens"] = max_tokens
            else:
                tool_params["max_tokens"] = max_tokens

            response: ChatCompletion = self.client.chat.completions.create(**tool_params)

            # Update statistics
            if response.usage:
                self.stats["total_input_tokens"] += response.usage.prompt_tokens
                self.stats["total_output_tokens"] += response.usage.completion_tokens

                cost = calculate_cost(
                    model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
                self.stats["total_cost"] += cost

            # Add the final response to conversation
            final_content = response.choices[0].message.content or ""
            if final_content:
                self.conversation.add_message(role="assistant", content=final_content)

            return final_content
        finally:
            # Always decrement recursion depth, even if an exception occurred
            self.tool_call_depth -= 1

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            **self.stats,
            "conversation_summary": self.conversation.get_summary(),
        }

    def reset(self, keep_system: bool = True):
        """Reset conversation"""
        self.conversation.clear_history(keep_system=keep_system)

        # Reset stats
        self.stats = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "tool_calls_made": 0,
        }
