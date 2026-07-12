#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
import subprocess
import shlex
import os
import json
from jinja2 import Environment, BaseLoader, FileSystemLoader


DOCUMENTATION = r'''
---
module: incus_cli

short_description: Execute Incus CLI commands with Jinja2 templating

version_added: "1.0.0"

description:
    - Execute Incus CLI commands on the target host
    - Supports Jinja2 templating for command generation
    - Accepts either a command string (can be multiline with YAML | notation) or a template file path
    - Handles Ansible variables, facts, and module parameters automatically
    - Supports remote Incus servers via the remote parameter
    - Supports Incus profiles via the profile parameter

options:
    command:
        description:
            - Command or commands to execute
            - Can be a single command string or multiline using YAML | notation
            - Will be rendered with Jinja2 using all available Ansible variables
            - Mutually exclusive with template parameter
            - Example: "incus {{ remote }}:launch {{ image }} {{ container_name }}"
            - Example multiline: |
                incus {{ remote }}:init {{ image }} {{ container_name }} --container
                incus {{ remote }}:start {{ container_name }}
        type: str
        required: false
        default: null
    template:
        description:
            - Path to Jinja2 template file containing commands
            - Template will be rendered with Jinja2 using all available Ansible variables
            - Mutually exclusive with command parameter
            - Example: "/path/to/incus_commands.j2"
        type: str
        required: false
        default: null
    remote:
        description:
            - Remote Incus server to target
            - Will be available as {{ remote }} in command templates
            - Example: "my-remote-server"
            - Command will be transformed to: incus <remote>:<command>
        type: str
        required: false
        default: null
    profile:
        description:
            - Incus profile to use for commands
            - Will be available as {{ profile }} in command templates
            - Example: "my-profile"
        type: str
        required: false
        default: null
    chdir:
        description:
            - Working directory for command execution
        type: str
        required: false
        default: null
    environment:
        description:
            - Dictionary of environment variables to set
        type: dict
        required: false
        default: {}
    ignore_errors:
        description:
            - Whether to ignore command execution errors
        type: bool
        required: false
        default: false
    return_output:
        description:
            - Whether to return command output in result
        type: bool
        required: false
        default: true

notes:
    - Requires Incus CLI to be installed on the target host
    - Requires Jinja2 to be installed on the target host (python3-jinja2)
    - Commands are executed with the same user as the Ansible connection
    - The remote parameter is automatically prefixed to Incus commands when specified
    - Either command or template must be provided, but not both

seealso:
    - name: incus command line tool
      description: Official Incus CLI documentation
      link: https://linuxcontainers.org/incus/docs/main/commands/

examples:
    - name: Launch a container on remote server using command
      incus_cli:
        command: "incus {{ remote }}:launch {{ image }} {{ container_name }}"
        remote: production-server
        profile: web-profile

    - name: Execute multiple commands with multiline notation
      incus_cli:
        command: |
          incus {{ remote }}:init {{ image }} {{ container_name }} --container
          incus {{ remote }}:config set {{ container_name }} user.data '{{ user_data | to_json }}'
          incus {{ remote }}:start {{ container_name }}
        remote: production-server

    - name: Use template file
      incus_cli:
        template: /templates/incus_launch.j2
        remote: production-server
        profile: web-profile

    - name: Simple command execution
      incus_cli:
        command: "incus list --format json"
        return_output: true

    - name: Add profile to container
      incus_cli:
        command: "incus profile add {{ container_name }} {{ profile }}"
        profile: my-profile

author:
    - Frédéric PERREAU
'''

EXAMPLES = r'''
- name: Create and start container on remote server
  incus_cli:
    command: |
      incus {{ remote }}:init {{ image }} {{ container_name }} --container
      incus {{ remote }}:start {{ container_name }}
    remote: my-remote-node
    profile: default
  vars:
    image: ubuntu:22.04
    container_name: web-app-01

- name: Get container list as JSON
  incus_cli:
    command: "incus {{ remote }}:list --format json"
    remote: my-remote-node
    return_output: true
  register: container_list

- name: Create profile and launch container using template
  incus_cli:
    template: templates/launch_container.j2
    remote: my-remote-node
    profile: custom-profile
  vars:
    image: ubuntu:22.04
    container_name: db-server-01

- name: Simple local command
  incus_cli:
    command: "incus list"
    return_output: true
'''

RETURN = r'''
stdout:
    description: Standard output of the executed commands
    type: str
    returned: when return_output is true
    sample: "{'containers': [{'name': 'my-container', 'status': 'Running'}]}"
stderr:
    description: Standard error of the executed commands
    type: str
    returned: always
    sample: ""
rc:
    description: Return code of the last executed command
    type: int
    returned: always
    sample: 0
commands_executed:
    description: List of commands that were executed
    type: list
    elements: str
    returned: always
    sample: ["incus my-remote:launch ubuntu:22.04 my-container"]
changed:
    description: Whether any changes were made
    type: bool
    returned: always
    sample: true
failed:
    description: Whether any command failed
    type: bool
    returned: always
    sample: false
template_path:
    description: Path to the template file used (if template parameter was provided)
    type: str
    returned: when template is used
    sample: "/templates/incus_launch.j2"
'''


class IncusCliModule:
    """Main module class for Incus CLI execution"""
    
    def __init__(self):
        # Define module argument specification
        self.module_args = dict(
            command=dict(type='str', required=False, default=None),
            template=dict(type='str', required=False, default=None),
            remote=dict(type='str', required=False, default=None),
            profile=dict(type='str', required=False, default=None),
            chdir=dict(type='str', required=False, default=None),
            environment=dict(type='dict', required=False, default={}),
            ignore_errors=dict(type='bool', required=False, default=False),
            return_output=dict(type='bool', required=False, default=True),
        )
        
        # Initialize the Ansible module
        self.module = AnsibleModule(
            argument_spec=self.module_args,
            supports_check_mode=True,
            mutually_exclusive=[
                ['command', 'template'],
            ],
            required_one_of=[
                ['command', 'template'],
            ],
        )
        
        # Get module parameters
        self.raw_command = self.module.params['command']
        self.template_path = self.module.params['template']
        self.remote = self.module.params['remote']
        self.profile = self.module.params['profile']
        self.chdir = self.module.params['chdir']
        self.environment = self.module.params['environment']
        self.ignore_errors = self.module.params['ignore_errors']
        self.return_output = self.module.params['return_output']

        self._inventory_hostname = getattr(self.module, '_inventory_hostname', None)
        self._inventory_hostname_short = getattr(self.module, '_inventory_hostname_short', None)
        self._playbook_dir = getattr(self.module, '_playbook_dir', None)
        self._role_path = getattr(self.module, '_role_path', None)

        # Initialize result dictionary
        self.result = {
            'changed': False,
            'failed': False,
            'stdout': '',
            'stderr': '',
            'rc': 0,
            'commands_executed': [],
        }
    
    def _render_template(self, template_content, variables):
        """Render Jinja2 template with Ansible variables"""
        try:
            # Create Jinja2 environment with Ansible-style filters
            env = Environment(
                loader=BaseLoader(),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            
            # Add common Ansible filters
            env.filters['to_json'] = json.dumps
            env.filters['to_nice_json'] = lambda x: json.dumps(x, indent=2)
            env.filters['bool'] = bool
            env.filters['int'] = int
            env.filters['float'] = float
            env.filters['string'] = str
            
            # Create template and render
            template = env.from_string(template_content)
            rendered = template.render(**variables)
            return rendered
        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to render template: {str(e)}",
                error=str(e),
                template=template_content
            )
    
    def _render_template_file(self, template_path, variables):
        """Render Jinja2 template file with Ansible variables"""
        try:
            # Get the directory of the template for FileSystemLoader
            template_dir = os.path.dirname(template_path) or '.'
            template_file = os.path.basename(template_path)
            
            # Create Jinja2 environment with FileSystemLoader
            env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            
            # Add common Ansible filters
            env.filters['to_json'] = json.dumps
            env.filters['to_nice_json'] = lambda x: json.dumps(x, indent=2)
            env.filters['bool'] = bool
            env.filters['int'] = int
            env.filters['float'] = float
            env.filters['string'] = str
            
            # Load and render template
            template = env.get_template(template_file)
            rendered = template.render(**variables)
            return rendered
        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to render template file {template_path}: {str(e)}",
                error=str(e),
                path=template_path
            )
    
    def _execute_command(self, command, cwd=None, env_vars=None):
        """Execute a single command via subprocess"""
        try:
            # Prepare environment
            final_env = os.environ.copy()
            if env_vars:
                final_env.update(env_vars)
            
            # Execute command
            process = subprocess.Popen(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=final_env,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            rc = process.returncode
            
            return {
                'stdout': stdout,
                'stderr': stderr,
                'rc': rc,
                'command': command
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'rc': 1,
                'command': command
            }
    
    def _get_ansible_variables(self):
        """Get all available Ansible variables and module parameters"""
        variables = {}
        
        # Add module parameters (excluding command and template which are handled separately)
        for param_name in ['remote', 'profile']:
            param_value = self.module.params.get(param_name)
            if param_value is not None:
                variables[param_name] = param_value
        
        # Add host variables
        if hasattr(self.module, '_host_vars'):
            variables.update(self.module._host_vars)
        
        # Add group variables
        if hasattr(self.module, '_group_vars'):
            for group, vars_dict in self.module._group_vars.items():
                variables[f'group_names.{group}'] = vars_dict
        
        # Add facts
        if hasattr(self.module, '_facts'):
            variables.update(self.module._facts)
        
        # Add special variables
        if self._inventory_hostname:
            variables['inventory_hostname'] = self._inventory_hostname
        if self._inventory_hostname_short:
            variables['inventory_hostname_short'] = self._inventory_hostname_short
        if self._playbook_dir:
            variables['playbook_dir'] = self._playbook_dir
        if self._role_path:
            variables['role_path'] = self._role_path
        
        return variables
    
    def _process_remote_command(self, command):
        """Process command to add remote prefix if specified"""
        if self.remote and command.strip().startswith('incus'):
            # Split the command to insert remote after 'incus'
            parts = command.split()
            if len(parts) >= 1 and parts[0] == 'incus':
                # Insert remote after 'incus' with colon
                parts.insert(1, f"{self.remote}:")
                return ' '.join(parts)
        return command
    
    def run(self):
        """Main execution method"""
        # Collect all Ansible variables and module parameters
        ansible_vars = self._get_ansible_variables()
        
        # Determine the source of commands (command string or template file)
        if self.template_path:
            # Render template file
            rendered_commands = self._render_template_file(self.template_path, ansible_vars)
            # Store template path in result for reference
            self.result['template_path'] = self.template_path
        else:
            # Render command string
            rendered_commands = self._render_template(self.raw_command, ansible_vars)
        
        # Split by newlines and filter empty lines
        commands_to_execute = [cmd.strip() for cmd in rendered_commands.split('\n') if cmd.strip()]
        
        # Check if we have commands to execute
        if not commands_to_execute:
            self.module.fail_json(
                msg="No commands to execute after template rendering."
            )
        
        # Process each command to add remote prefix if specified
        processed_commands = []
        for cmd in commands_to_execute:
            processed_cmd = self._process_remote_command(cmd)
            processed_commands.append(processed_cmd)
        
        # Execute each command
        all_stdout = []
        all_stderr = []
        overall_rc = 0
        execution_failed = False
        
        for command in processed_commands:
            # Record command execution
            self.result['commands_executed'].append(command)
            
            # Execute command
            exec_result = self._execute_command(
                command,
                cwd=self.chdir,
                env_vars=self.environment
            )
            
            all_stdout.append(exec_result['stdout'])
            all_stderr.append(exec_result['stderr'])
            
            # Update overall return code
            if exec_result['rc'] != 0:
                overall_rc = exec_result['rc']
                execution_failed = True
            
            # Set changed if command succeeded and wasn't a read-only operation
            if exec_result['rc'] == 0:
                read_only_commands = ['list', 'info', 'show', 'config get']
                if not any(cmd in command.lower() for cmd in read_only_commands):
                    self.result['changed'] = True
        
        # Aggregate output
        self.result['stdout'] = '\n'.join(all_stdout) if self.return_output else ''
        self.result['stderr'] = '\n'.join(all_stderr)
        self.result['rc'] = overall_rc
        
        # Handle errors
        if execution_failed and not self.ignore_errors:
            self.result['failed'] = True
            self.module.fail_json(
                msg=f"Command execution failed with rc={overall_rc}",
                **self.result
            )
        elif execution_failed:
            self.result['failed'] = True
        
        # Return success
        self.module.exit_json(**self.result)


def main():
    """Module entry point"""
    module = IncusCliModule()
    module.run()


if __name__ == '__main__':
    main()
