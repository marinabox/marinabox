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


class GraphState(TypedDict):
    input_task: str
    conversation_history: list
    sams_thought: str
    screen_description: str
    steps_taken_by_computer_guy: str

class ShouldContinueOutput(BaseModel):
    should_continue: str

def claude_the_vision_guy(state: GraphState):
    responses = mb.computer_use_command("samthropic", """Describe the current page that you are viewing on Chrome currently in detail.
                                Make sure to scroll down a bit and also give me what is below in the page. 
                                Make sure to describe the page in detail and give me a detailed description of the page.""")
        
    
    # Collect all responses into a readable format
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

def sam_the_thinker(state: GraphState):
    if state['sams_thought'] == '':
        input_task = input("Enter the task to perform: ")
        print("INPUT TASK: ", state['input_task'])
        state['input_task'] = input_task

        first_message = f"You are sitting opposite to a person who has access to a computer in which a browser is open. Nothing else on the computer is accessible and the person will only be able to use the browser. Only the person can see the monitor screen and not you. You will be given a task to perform on the browser. Based on the task, you will give step by step instructions on how to perform the task. Make sure to give step by step instructions and MAKE SURE TO GIVE ONLY ONE STEP AT A TIME. At each step the person will try to execute it on the computer and tell you what they did and what they see on the screen. Based on that you will give the next step. Once the user has completed the entire task, you can indicate the the task is complete.  This is what the user currently sees on the screen: {state['screen_description']}. The task to do is the following Task: {state['input_task']}"
        state['conversation_history'].append(HumanMessage(content=first_message))


    prompt = ChatPromptTemplate.from_messages(state['conversation_history'])

    llm = ChatOpenAI(
        model="o1-preview",
        temperature=1,
        max_tokens=None
    )

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
    
    messages = [SystemMessage(content="A certain person is giving insturctions to another person who has access to a computer to perform something on the computer. You have to determine by looking at the conversation history whether the person has completed the task or not. If they have completed the task, you should return 'should_not_continue'. If they have not completed the task, you should return 'should_continue'.")]

    messages.append(HumanMessage(content=f"The last message from the person giving instructions is: {state['conversation_history'][-1].content}"))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | lm_structured
    response = chain.invoke({})
    should_continue = response.should_continue

    # should_continue = input("Enter should_continue or not")
    print("SHOULD CONTINUE: ", should_continue)

    if should_continue == "should_continue":
        return Command(goto="claude_the_computer_guy")
    else:
        print("ENDING THE AGENT")
        return Command(goto=END)

def claude_the_computer_guy(state: GraphState):

    print("\n\nCOMMAND TO THE COMPUTER GUY: ", "This is the current step you have to perform: " + state['sams_thought'] + ". On the page that you are viewing on Chrome currently, Stricly only perform the following step after analyzing the page : " + state['sams_thought'] + "\n\n")

    responses = mb.computer_use_command("samthropic", "This is the overall task: " + state['input_task'] + ". This is the current step: " + state['sams_thought'] + ". On the page that you are viewing on Chrome currently, ONLY perform the following action after analyzing the page : " + state['sams_thought'])
    
    # Collect all responses into a readable format
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


print("Initializing the samthropic agent")

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

def setup_output_directories():
    Path("outputs/logs").mkdir(parents=True, exist_ok=True)
    Path("outputs/videos").mkdir(parents=True, exist_ok=True)

def process_single_task(task_data):
    # Initialize SDK with custom video path
    
    # Setup logging
    log_file = f"outputs/logs/{task_data['id']}.txt"
    original_stdout = sys.stdout
    original_stdin = sys.stdin
    
    # Create a custom stdout class to write to both file and console
    class DualOutput:
        def __init__(self, file_obj, original_stdout):
            self.file_obj = file_obj
            self.original_stdout = original_stdout
        
        def write(self, text):
            self.file_obj.write(text)
            self.original_stdout.write(text)
            
        def flush(self):
            self.file_obj.flush()
            self.original_stdout.flush()
    
    f = open(log_file, 'w')
    sys.stdout = DualOutput(f, original_stdout)

    # Create a custom stdin class to simulate terminal input
    class CustomStdin:
        def __init__(self, input_text):
            self.input_text = input_text
        
        def readline(self):
            return self.input_text + '\n'

    # Format the question and set up custom stdin
    formatted_question = f"{task_data['ques']} using {task_data['web']}"
    sys.stdin = CustomStdin(formatted_question)

    # Set up API keys and create session
    # Add your anthropic key here
    mb.set_anthropic_key()
    # Add your openai key here
    os.environ['OPENAI_API_KEY'] = 
    
    session = mb.create_session(env_type="browser", tag="samthropic")
    session_id = session.session_id

    # Run the agent with empty input_task (will be filled via stdin)
    samthropic_agent.invoke({
        "input_task": "", 
        "conversation_history": [], 
        "sams_thought": "", 
        "screen_description": "", 
        "steps_taken_by_computer_guy": ""
    }, {"recursion_limit": 500})

    # Clean up
    mb.stop_session(session_id, video_filename=f"{task_data['id']}.mp4")
    sys.stdout = original_stdout
    sys.stdin = original_stdin
    f.close()

# Replace the main execution code at the bottom with:
if __name__ == "__main__":
    setup_output_directories()
    
    # Read tasks from input file
    with open('input_tasks.json', 'r') as f:
        tasks = json.load(f)
    
    # Process each task
    for task in tasks:
        process_single_task(task)
    
# Provide a recipe for vegetarian lasagna with more than 100 reviews and a rating of at least 4.5 stars suitable for 6 people on the website https://www.allrecipes.com/.