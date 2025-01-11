# samthropic.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, Field
from langgraph.graph import END, StateGraph, START
import os
from typing import List, TypedDict
from marinabox import MarinaboxSDK
from langgraph.types import Command
import json
import sys
from pathlib import Path

mb = MarinaboxSDK(videos_path="outputs/videos")

# Get the marinabox package root directory
MARINABOX_ROOT = Path(__file__).parent

class GraphState(TypedDict):
    input_task: str
    conversation_history: list
    sams_thought: str
    screen_description: str
    steps_taken_by_computer_guy: str
    session_id: str

class ShouldContinueOutput(BaseModel):
    should_continue: str

def claude_the_vision_guy(state: GraphState):
    responses = mb.computer_use_command("samthropic", """Describe the current page that you are viewing on Chrome currently in detail.
                                Make sure to scroll down a bit and also give me what is below in the page. 
                                Make sure to describe the page in detail and give me a detailed description of the page.""")
        
    computer_response = []
    for resp in responses:
        if resp[0] == "text":
            computer_response.append(f"Computer User's thought: {resp[1]}")
        elif resp[0] == "tool_output":
            computer_response.append(f"Result from the computer user's action: {resp[1]}")
        elif resp[0] == "tool_use":
            computer_response.append(f"Action taken by the computer user: Using {resp[1]} with {resp[2]}")
        elif resp[0] == "tool_error":
            computer_response.append(f"Error encountered by the computer user: {resp[1]}")
    
    formatted_response = "\n".join(computer_response)
    state['screen_description'] = formatted_response
    print("SCREEN DESCRIPTION: ", state['screen_description'],"\n\n")

    if state["steps_taken_by_computer_guy"] != '':
        state['conversation_history'].append(HumanMessage(content=f"""DESCRIPTION OF THE PAGE:\n{state['screen_description']}.
        COMPUTER USERS THOUGHTS AND STEPS:\n{state['steps_taken_by_computer_guy']}. Now, make sure the previous step given by you was correctly executed if not make sure to give the correct instruction to go back and do that step based on current state. If the previous step was successful and you are satisfied then based on your previous instructions and what the computer user has conveyed, give me the next step that I need to take. If you truly think the entire task is complete and the exact question/task is answered/done, then tell me that it is done. Before you say its done make sure that if a question needs to be answered, you tell me the answer and then say its done.
        Analyze and think through as much as needed deeply and plan in detail and give me the answer."""))

    return state

def get_next_input(session_id: str) -> str:
    """Get the next input from the queue file created by the UI"""
    input_file = Path(f"marinabox/data/input_queue/{session_id}.txt")
    
    if not input_file.exists():
        return None
        
    try:
        with open(input_file, "r+") as f:
            lines = f.readlines()
            if not lines:
                return None
                
            next_input = lines[0].strip()
            
            # Remove the processed input
            f.seek(0)
            f.writelines(lines[1:])
            f.truncate()
            
            return next_input
    except Exception as e:
        print(f"Error reading input queue: {e}")
        return None

def sam_the_thinker(state: GraphState):
    if state['sams_thought'] == '':
        # Get input from the UI via the input queue
        next_input = get_next_input(state['session_id'])
        
        if next_input:
            state['input_task'] = next_input
            
            first_message = f"""You are sitting opposite to a person who has access to a computer in which a browser is open. Nothing else on the computer is accessible and the person will only be able to use the browser. Only the person can see the monitor screen and not you. You will be given a task to perform on the browser. Based on the task, you will give step by step instructions on how to perform the task. Make sure to give step by step instructions and MAKE SURE TO GIVE ONLY ONE STEP AT A TIME. At each step the person will try to execute it on the computer and tell you what they did and what they see on the screen. Based on that you will give the next step. Once the user has completed the entire task, you can indicate the the task is complete.  This is what the user currently sees on the screen: {state['screen_description']}. The task to do is the following Task: {state['input_task']}"""
            
            state['conversation_history'].append(HumanMessage(content=first_message))
        else:
            # If no input is available, return current state and wait
            return state

    prompt = ChatPromptTemplate.from_messages(state['conversation_history'])
    llm = ChatOpenAI(model="o1-preview", temperature=1, max_tokens=None)
    chain = prompt | llm
    response = chain.invoke({})
    sams_thought = response.content
    state['conversation_history'].append(AIMessage(content=sams_thought))
    state['sams_thought'] = sams_thought
    print("SAMS THOUGHT: ", sams_thought)
    return state

def should_continue(state: GraphState):
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0    
    )
    
    lm_structured = llm.with_structured_output(ShouldContinueOutput)
    
    messages = [SystemMessage(content="A certain person is giving instructions to another person who has access to a computer to perform something on the computer. You have to determine by looking at the conversation history whether the person has completed the task or not. If they have completed the task, you should return 'should_not_continue'. If they have not completed the task, you should return 'should_continue'.")]

    # messages.append(HumanMessage(content=f"The last message from the person giving instructions is: {state['conversation_history'][-1].content}"))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | lm_structured
    response = chain.invoke({})
    should_continue = response.should_continue

    print("SHOULD CONTINUE: ", should_continue)

    if should_continue == "should_continue":
        return Command(goto="claude_the_computer_guy")
    else:
        print("ENDING THE AGENT")
        return Command(goto=END)

def claude_the_computer_guy(state: GraphState):
    print("\n\nCOMMAND TO THE COMPUTER GUY: ", "This is the current step you have to perform: " + state['sams_thought'] + ". On the page that you are viewing on Chrome currently, Strictly only perform the following step after analyzing the page : " + state['sams_thought'] + "\n\n")

    responses = mb.computer_use_command("samthropic", "This is the overall task: " + state['input_task'] + ". This is the current step: " + state['sams_thought'] + ". On the page that you are viewing on Chrome currently, ONLY perform the following action after analyzing the page : " + state['sams_thought'])
    
    computer_response = []
    for resp in responses:
        if resp[0] == "text":
            computer_response.append(f"Computer User's thought: {resp[1]}")
        elif resp[0] == "tool_output":
            computer_response.append(f"Result from the computer user's action: {resp[1]}")
        elif resp[0] == "tool_use":
            computer_response.append(f"Action taken by the computer user: Using {resp[1]} with {resp[2]}")
        elif resp[0] == "tool_error":
            computer_response.append(f"Error encountered by the computer user: {resp[1]}")
    
    formatted_response = "\n".join(computer_response)
    state['steps_taken_by_computer_guy'] = formatted_response
    return state

def setup_output_directories():
    """Create necessary directories for outputs"""
    Path("outputs/logs").mkdir(parents=True, exist_ok=True)
    Path("outputs/videos").mkdir(parents=True, exist_ok=True)
    Path("marinabox/data/console_logs").mkdir(parents=True, exist_ok=True)
    Path("marinabox/data/input_queue").mkdir(parents=True, exist_ok=True)

def run_samthropic_session(session_id: str):
    """Run the samthropic agent for a session"""
    try:
        # Set up logging
        log_console = f"marinabox/data/console_logs/{session_id}.txt"
        Path(log_console).parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_console, 'w') as f_session:
            # Redirect stdout to file
            import sys
            original_stdout = sys.stdout
            sys.stdout = f_session

            # Initialize workflow
            workflow = StateGraph(GraphState)
            workflow.add_node("sam_the_thinker", sam_the_thinker)
            workflow.add_node("claude_the_computer_guy", claude_the_computer_guy)
            workflow.add_node("claude_the_vision_guy", claude_the_vision_guy)
            workflow.add_node("should_continue", should_continue)
            workflow.add_edge(START, "claude_the_vision_guy")
            workflow.add_edge("claude_the_vision_guy", "sam_the_thinker")
            workflow.add_edge("sam_the_thinker", "should_continue")
            workflow.add_edge("claude_the_computer_guy", "claude_the_vision_guy")
            
            samthropic_agent = workflow.compile()

            # Initialize the agent state
            samthropic_agent.invoke({
                "input_task": "", 
                "conversation_history": [], 
                "sams_thought": "", 
                "screen_description": "", 
                "steps_taken_by_computer_guy": "",
                "session_id": session_id
            }, {"recursion_limit": 500})

            # Restore stdout
            sys.stdout = original_stdout

    except Exception as e:
        print(f"Error in samthropic session: {e}")

if __name__ == "__main__":
    setup_output_directories()
    
       # Set up API keys and create session
    # Add your anthropic key here
    mb.set_anthropic_key("your-key")
    os.environ['OPENAI_API_KEY'] = "your-key"
    
    # Create session
    session = mb.create_session(env_type="browser", tag="samthropic")
    session_id = session.session_id
    
    run_samthropic_session(session_id)