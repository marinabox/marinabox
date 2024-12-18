from typing import List, Optional
import boto3
import json
from datetime import datetime
import pickle
import io
import time

from .models import BrowserSession
from .config import AWSConfig

class AWSContainerManager:
    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            self._setup_debug_logging()
        
        self.aws_config = AWSConfig()
        if self.debug:
            print("DEBUG: Initializing AWS session")
        
        try:
            self.session = self.aws_config.get_session()
            self.ecs = self.session.client('ecs')
            self.s3 = self.session.client('s3')
            self.ec2 = self.session.client('ec2')
            
            if self.debug:
                print("DEBUG: Successfully initialized AWS clients")
                print(f"DEBUG: Using region: {self.session.region_name}")
        except Exception as e:
            print(f"ERROR: Failed to initialize AWS clients: {str(e)}")
            raise
        
        self.sessions = {}
        self.closed_sessions = {}
        
        # Check if bucket exists before trying to load sessions
        try:
            self.s3.head_bucket(Bucket=self.aws_config.bucket_name)
            if self.debug:
                print("DEBUG: Loading sessions from S3")
            self._load_sessions()
            self._load_closed_sessions()
        except self.s3.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['404', '403']:  # Bucket doesn't exist or we can't access it
                if self.debug:
                    print(f"DEBUG: S3 bucket {self.aws_config.bucket_name} not found - will be created during initialization")
            else:
                raise  # Re-raise if it's a different error
    
    def _setup_debug_logging(self):
        """Setup detailed AWS SDK debugging"""
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Enable boto3 debugging
        boto3_logger = logging.getLogger('boto3')
        boto3_logger.setLevel(logging.DEBUG)
        
        # Enable botocore debugging
        botocore_logger = logging.getLogger('botocore')
        botocore_logger.setLevel(logging.DEBUG)
    
    def _get_s3_key(self, key: str) -> str:
        """Generate S3 key with proper prefix"""
        return f"sessions/{key}"
    
    def _save_sessions(self):
        """Save active sessions to S3"""
        try:
            buffer = io.BytesIO()
            pickle.dump(self.sessions, buffer)
            self.s3.put_object(
                Bucket=self.aws_config.bucket_name,
                Key=self._get_s3_key("active_sessions.pkl"),
                Body=buffer.getvalue()
            )
        except Exception as e:
            print(f"Error saving sessions to S3: {str(e)}")
    
    def _save_closed_sessions(self):
        """Save closed sessions to S3"""
        try:
            buffer = io.BytesIO()
            pickle.dump(self.closed_sessions, buffer)
            self.s3.put_object(
                Bucket=self.aws_config.bucket_name,
                Key=self._get_s3_key("closed_sessions.pkl"),
                Body=buffer.getvalue()
            )
        except Exception as e:
            print(f"Error saving closed sessions to S3: {str(e)}")
    
    def _load_sessions(self):
        """Load active sessions from S3"""
        try:
            response = self.s3.get_object(
                Bucket=self.aws_config.bucket_name,
                Key=self._get_s3_key("active_sessions.pkl")
            )
            self.sessions = pickle.loads(response['Body'].read())
            
            # Add debug logging
            if self.debug:
                print(f"DEBUG: Loaded {len(self.sessions)} sessions from S3")
            
            # Verify tasks still exist
            tasks_response = self.ecs.list_tasks(
                cluster='marinabox',
                desiredStatus='RUNNING'
            )
            active_tasks = {
                task.split('/')[-1]
                for task in tasks_response.get('taskArns', [])
            }
            
            if self.debug:
                print(f"DEBUG: Found {len(active_tasks)} active ECS tasks")
            
            # Remove stale sessions
            stale_sessions = [
                session_id for session_id in list(self.sessions.keys())
                if session_id not in active_tasks
            ]
            for session_id in stale_sessions:
                if self.debug:
                    print(f"DEBUG: Removing stale session: {session_id}")
                del self.sessions[session_id]
            
            if stale_sessions:
                self._save_sessions()
                
        except self.s3.exceptions.NoSuchKey:
            if self.debug:
                print("DEBUG: No existing sessions file found in S3")
            self.sessions = {}
        except self.s3.exceptions.NoSuchBucket:
            if self.debug:
                print("DEBUG: S3 bucket not found - will be created during initialization")
            self.sessions = {}
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Error loading sessions from S3: {str(e)}")
            self.sessions = {}
    
    def _load_closed_sessions(self):
        """Load closed sessions from S3"""
        try:
            response = self.s3.get_object(
                Bucket=self.aws_config.bucket_name,
                Key=self._get_s3_key("closed_sessions.pkl")
            )
            self.closed_sessions = pickle.loads(response['Body'].read())
        except (self.s3.exceptions.NoSuchKey, self.s3.exceptions.NoSuchBucket):
            if self.debug:
                print("DEBUG: No closed sessions found in S3")
            self.closed_sessions = {}
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Error loading closed sessions from S3: {str(e)}")
            self.closed_sessions = {}
    
    def create_session(self, resolution: str = "1280x800x24", subnet_id: str = None, security_group_id: str = None) -> BrowserSession:
        """Create a new browser session in AWS ECS"""
        start_time = time.time()
        
        try:
            print(f"[{time.time() - start_time:.2f}s] Starting session creation...")
            
            print(f"[{time.time() - start_time:.2f}s] Getting task definition ARN...")
            task_definition_arn = self._get_task_definition_arn()
            print(f"[{time.time() - start_time:.2f}s] Got task definition: {task_definition_arn}")
            
            if not subnet_id:
                print(f"[{time.time() - start_time:.2f}s] Getting subnet ID...")
                subnet_id = self._get_subnet_id()
                print(f"[{time.time() - start_time:.2f}s] Got subnet ID: {subnet_id}")
            
            print(f"[{time.time() - start_time:.2f}s] Creating ECS task...")
            network_config = {
                'awsvpcConfiguration': {
                    'subnets': [subnet_id],
                    'assignPublicIp': 'ENABLED'
                }
            }
            
            if security_group_id:
                network_config['awsvpcConfiguration']['securityGroups'] = [security_group_id]
            
            response = self.ecs.run_task(
                cluster='marinabox',
                taskDefinition=task_definition_arn,
                launchType='FARGATE',
                networkConfiguration=network_config,
                platformVersion='1.4.0',
                enableExecuteCommand=True,
                overrides={
                    'containerOverrides': [{
                        'name': 'marinabox',
                        'environment': [
                            {'name': 'RESOLUTION', 'value': resolution}
                        ]
                    }]
                }
            )
            print(f"[{time.time() - start_time:.2f}s] ECS task created")
            
            task = response['tasks'][0]
            task_id = task['taskArn'].split('/')[-1]
            print(f"[{time.time() - start_time:.2f}s] Task ID: {task_id}")
            
            print(f"[{time.time() - start_time:.2f}s] Getting WebSocket URL...")
            websocket_url = self._get_websocket_url(task_id)
            print(f"[{time.time() - start_time:.2f}s] WebSocket URL retrieved: {'Success' if websocket_url else 'Failed'}")
            
            print(f"[{time.time() - start_time:.2f}s] Creating session object...")
            session = BrowserSession(
                session_id=task_id,
                container_id=task['containers'][0]['containerArn'],
                debug_port=9222,
                vnc_port=6081,
                created_at=datetime.utcnow(),
                resolution=resolution,
                websocket_url=websocket_url
            )
            
            print(f"[{time.time() - start_time:.2f}s] Saving session to S3...")
            self.sessions[task_id] = session
            self._save_sessions()
            
            total_time = time.time() - start_time
            print(f"[{total_time:.2f}s] Session creation completed")
            
            return session
            
        except Exception as e:
            print(f"[{time.time() - start_time:.2f}s] Error creating session: {str(e)}")
            raise
    
    def list_sessions(self) -> List[BrowserSession]:
        """List all active sessions"""
        if self.debug:
            print("DEBUG: Listing active sessions")
            print("DEBUG: Checking ECS tasks")
        
        try:
            # Get all running tasks
            response = self.ecs.list_tasks(
                cluster='marinabox',
                desiredStatus='RUNNING'
            )
            
            if self.debug:
                print(f"DEBUG: Found {len(response.get('taskArns', []))} tasks")
            
            if not response.get('taskArns'):
                if self.debug:
                    print("DEBUG: No active tasks found")
                return []
            
            # Get detailed task information
            task_details = self.ecs.describe_tasks(
                cluster='marinabox',
                tasks=response['taskArns']
            )
            
            if self.debug:
                print("DEBUG: Retrieved task details")
                print(f"DEBUG: Task details: {json.dumps(task_details, indent=2)}")
            
            # Update sessions based on task information
            active_sessions = []
            for task in task_details['tasks']:
                task_id = task['taskArn'].split('/')[-1]
                if task_id in self.sessions:
                    session = self.sessions[task_id]
                    session.runtime_seconds = session.get_current_runtime()
                    active_sessions.append(session)
                    
                    if self.debug:
                        print(f"DEBUG: Found active session {task_id}")
            
            return active_sessions
            
        except self.ecs.exceptions.ClusterNotFoundException:
            if self.debug:
                print("ERROR: ECS cluster 'marinabox' not found")
            return []
        except Exception as e:
            if self.debug:
                print(f"ERROR: Failed to list sessions: {str(e)}")
                import traceback
                traceback.print_exc()
            raise
    
    def list_closed_sessions(self) -> List[BrowserSession]:
        """List all closed AWS sessions"""
        return list(self.closed_sessions.values())
    
    def get_closed_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get details for a specific closed session"""
        return self.closed_sessions.get(session_id)
    
    def stop_session(self, session_id: str) -> bool:
        """Stop an AWS browser session"""
        if session_id not in self.sessions:
            return False
            
        try:
            # Stop the ECS task
            self.ecs.stop_task(
                cluster='marinabox',
                task=session_id,
                reason='User requested stop'
            )
            
            # Get the session and update its status
            session = self.sessions[session_id]
            session.status = "stopped"
            session.closed_at = datetime.utcnow()
            session.runtime_seconds = (session.closed_at - session.created_at).total_seconds()
            
            # Copy recording if available
            try:
                # Stop ffmpeg first to ensure video is properly finalized
                self.ecs.execute_command(
                    cluster='marinabox',
                    task=session_id,
                    container='marinabox',
                    command=['/usr/bin/supervisorctl', '-c', '/etc/supervisor.d/supervisord.ini', 'stop', 'ffmpeg']
                )
                time.sleep(2)  # Wait for ffmpeg to finish

                # Upload directly from container to S3 using AWS CLI
                video_key = f"recordings/{session_id}.mp4"
                self.ecs.execute_command(
                    cluster='marinabox',
                    task=session_id,
                    container='marinabox',
                    command=['aws', 's3', 'cp', '/tmp/session.mp4', f's3://{self.aws_config.bucket_name}/{video_key}']
                )
                
                session.video_path = f"s3://{self.aws_config.bucket_name}/{video_key}"
            except Exception as e:
                print(f"Error copying recording: {str(e)}")
            
            # Move to closed sessions
            self.closed_sessions[session_id] = session
            del self.sessions[session_id]
            
            # Save both session lists
            self._save_sessions()
            self._save_closed_sessions()
            
            return True
            
        except Exception as e:
            print(f"Failed to stop AWS session: {str(e)}")
            return False
    
    def _get_task_definition_arn(self) -> str:
        """Get the latest active task definition ARN"""
        response = self.ecs.list_task_definitions(
            familyPrefix='marinabox',
            status='ACTIVE',
            sort='DESC',
            maxResults=1
        )
        if not response['taskDefinitionArns']:
            raise Exception("No task definition found. Please run 'mb aws init' first.")
        return response['taskDefinitionArns'][0]
    
    def _get_subnet_id(self) -> str:
        """Get the first available subnet ID"""
        response = self.ec2.describe_subnets(
            Filters=[{
                'Name': 'state',
                'Values': ['available']
            }]
        )
        if not response['Subnets']:
            raise Exception("No available subnets found")
        return response['Subnets'][0]['SubnetId']
    
    def _get_websocket_url(self, task_id: str) -> Optional[str]:
        """Get the WebSocket URL for Chrome DevTools"""
        import time
        start_time = time.time()
        
        try:
            print(f"[{time.time() - start_time:.2f}s] Waiting for task to be running...")
            waiter = self.ecs.get_waiter('tasks_running')
            waiter.wait(
                cluster='marinabox',
                tasks=[task_id]
            )
            print(f"[{time.time() - start_time:.2f}s] Task is now running")
            
            print(f"[{time.time() - start_time:.2f}s] Getting task details...")
            task = self.ecs.describe_tasks(
                cluster='marinabox',
                tasks=[task_id]
            )['tasks'][0]
            
            print(f"[{time.time() - start_time:.2f}s] Getting network interface ID...")
            eni = task['attachments'][0]['details']
            eni_id = next(detail['value'] for detail in eni if detail['name'] == 'networkInterfaceId')
            
            print(f"[{time.time() - start_time:.2f}s] Getting public IP from network interface...")
            eni_info = self.ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
            public_ip = eni_info['NetworkInterfaces'][0]['Association']['PublicIp']
            print(f"[{time.time() - start_time:.2f}s] Got public IP: {public_ip}")
            
            print(f"[{time.time() - start_time:.2f}s] Attempting to connect to Chrome debugger...")
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    response = requests.get(f"http://{public_ip}:9222/json/version", timeout=5)
                    print(f"[{time.time() - start_time:.2f}s] Successfully connected to debugger on attempt {attempt + 1}")
                    return response.json().get('webSocketDebuggerUrl')
                except:
                    print(f"[{time.time() - start_time:.2f}s] Connection attempt {attempt + 1} failed, retrying...")
                    time.sleep(2)
            
            print(f"[{time.time() - start_time:.2f}s] Failed to connect to debugger after {max_retries} attempts")
            return None
            
        except Exception as e:
            print(f"[{time.time() - start_time:.2f}s] Error getting WebSocket URL: {str(e)}")
            return None
    
    def verify_aws_setup(self) -> bool:
        """Verify that all required AWS resources are properly set up"""
        try:
            # Check ECS cluster exists
            clusters = self.ecs.list_clusters()
            if not any(c.endswith('/marinabox') for c in clusters.get('clusterArns', [])):
                return False
            
            # Check task definition exists
            task_defs = self.ecs.list_task_definitions(familyPrefix='marinabox', status='ACTIVE')
            if not task_defs.get('taskDefinitionArns', []):
                return False
            
            # Check ECR repository exists
            try:
                self.session.client('ecr').describe_repositories(repositoryNames=[self.aws_config.repository_name])
            except:
                return False
            
            # Check S3 bucket exists
            try:
                self.s3.head_bucket(Bucket=self.aws_config.bucket_name)
            except:
                return False
            
            return True
        
        except Exception as e:
            if self.debug:
                print(f"DEBUG: AWS setup verification failed: {str(e)}")
            return False