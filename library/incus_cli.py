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
            profile=dict(type='str', required=False, default="Default"),
            chdir=dict(type='str', required=False, default=None),
            environment=dict(type='dict', required=False, default={}),
            ignore_errors=dict(type='bool', required=False, default=False),
            return_output=dict(type='bool', required=False, default=True),
            image=dict(type='str', required=False, default=None),
            container=dict(type='str', required=False, default=None),
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
            'rendered_commands': [],
            'debug_info': {},  # Add debug information storage
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
            
            # Read template content for debugging
            template_content = None
            if os.path.exists(template_path):
                with open(template_path, 'r') as f:
                    template_content = f.read()
                self.result['debug_info']['template_content'] = template_content
                self.result['debug_info']['template_path'] = template_path
                self.result['debug_info']['template_exists'] = True
            else:
                self.result['debug_info']['template_exists'] = False
            
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
            
            self.result['debug_info']['variables_passed_count'] = len(variables)
            self.result['debug_info']['variables_passed_keys'] = list(variables.keys())
            
            rendered = template.render(**variables)
            
            self.result['debug_info']['rendered_output'] = rendered
            self.result['debug_info']['rendered_length'] = len(rendered)
            
            if rendered == "incus launch":
                self.result['debug_info']['warning'] = "Rendered to 'incus launch' without arguments - variables not substituted!"
            
            return rendered
        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to render template file {template_path}: {str(e)}",
                error=str(e),
                path=template_path,
                available_variables=variables,
                debug_info=self.result['debug_info']
            )
    
    def _execute_command(self, command, cwd=None, env_vars=None):
        """Execute a single command via subprocess"""
        # Remove comments from command (everything after #)
        command_cleaned = self._remove_comments(command)
        command_cleaned = command_cleaned.strip()
        
        if not command_cleaned:
            # Command is empty after removing comments - silently skip
            return {
                'stdout': '',
                'stderr': '',
                'rc': 0,
                'command': command
            }
        
        try:
            # Prepare environment
            final_env = os.environ.copy()
            if env_vars:
                final_env.update(env_vars)
            
            # Execute command
            process = subprocess.Popen(
                shlex.split(command_cleaned),
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
    
    def _remove_comments(self, line):
        """Remove comments from a command line (# and everything after)"""
        # Find the position of # (but not if it's inside quotes)
        in_single_quote = False
        in_double_quote = False
        
        for i, char in enumerate(line):
            # Toggle quote flags
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            # If we find # outside of quotes, truncate here
            elif char == '#' and not in_single_quote and not in_double_quote:
                return line[:i]
        
        # No comment found
        return line
    
    def _get_ansible_variables(self):
        """Get all available Ansible variables and module parameters"""
        variables = {}
        debug_info = {}
        
        # PRIORITY 1: Get all Ansible context variables (this includes playbook vars:, host_vars, group_vars, facts)
        # This is the PRIMARY source for Ansible variables
        if hasattr(self.module, 'vars') and self.module.vars:
            debug_info['module_vars_found'] = list(self.module.vars.keys())
            variables.update(self.module.vars)
        else:
            debug_info['module_vars_found'] = None
        
        # PRIORITY 2: Add module parameters (these override context variables)
        module_params = {}
        for param_name, param_value in self.module.params.items():
            if param_name in ('command', 'template'):
                continue
            if param_value is not None:
                module_params[param_name] = param_value
                variables[param_name] = param_value
        
        if module_params:
            debug_info['module_params_found'] = list(module_params.keys())
        
        # PRIORITY 3: Add fallback host variables (for compatibility)
        if hasattr(self.module, '_host_vars') and self.module._host_vars:
            host_vars = {k: v for k, v in self.module._host_vars.items() if k not in variables}
            if host_vars:
                debug_info['host_vars_found'] = list(host_vars.keys())
                variables.update(host_vars)
        
        # PRIORITY 4: Add fallback group variables (for compatibility)
        if hasattr(self.module, '_group_vars') and self.module._group_vars:
            group_vars_added = {}
            for group, vars_dict in self.module._group_vars.items():
                if vars_dict:
                    for key, value in vars_dict.items():
                        if key not in variables:
                            group_vars_added[key] = value
                            variables[key] = value
            if group_vars_added:
                debug_info['group_vars_found'] = list(group_vars_added.keys())
        
        # PRIORITY 5: Add facts (for compatibility)
        if hasattr(self.module, '_facts') and self.module._facts:
            facts_added = {k: v for k, v in self.module._facts.items() if k not in variables}
            if facts_added:
                debug_info['facts_found'] = list(facts_added.keys())
                variables.update(facts_added)
        
        # PRIORITY 6: Add special variables
        if self._inventory_hostname and 'inventory_hostname' not in variables:
            variables['inventory_hostname'] = self._inventory_hostname
        if self._inventory_hostname_short and 'inventory_hostname_short' not in variables:
            variables['inventory_hostname_short'] = self._inventory_hostname_short
        if self._playbook_dir and 'playbook_dir' not in variables:
            variables['playbook_dir'] = self._playbook_dir
        if self._role_path and 'role_path' not in variables:
            variables['role_path'] = self._role_path
        
        debug_info['total_vars'] = len(variables)
        debug_info['var_keys'] = sorted(list(variables.keys()))
        debug_info['image_var'] = variables.get('image', 'NOT FOUND')
        debug_info['container_var'] = variables.get('container', 'NOT FOUND')
        
        self.result['debug_info'] = debug_info

        return variables
    
    def _process_remote_command(self, command):
        """Process command to add remote prefix if specified"""
        if self.remote and command.strip().startswith('incus'):
            parts = command.split()
            # Find positional arguments (those not starting with -)
            positionals_info = []
            for i in range(1, len(parts)):
                if not parts[i].startswith('-'):
                    positionals_info.append((i, parts[i]))
            
            # Check if this is an instance creation command
            creation_commands = ['launch', 'init', 'create']
            if len(positionals_info) > 1:
                if positionals_info[0][1] in creation_commands:
                    # The instance name is the last positional argument
                    # Syntax: incus init images:debian/13 incusos1:c3 --vm
                    instance_idx, instance_name = positionals_info[-1]
                    # Only add remote if not already specified
                    if ':' not in instance_name:
                        parts[instance_idx] = f"{self.remote}:{instance_name}"
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
        
        # Filter out comment-only lines
        commands_to_execute = [cmd for cmd in commands_to_execute if not cmd.startswith('#')]
        
        # Check if we have commands to execute
        if not commands_to_execute:
            self.module.fail_json(
                msg="No commands to execute after template rendering.",
                available_variables=ansible_vars,
                rendered_output=rendered_commands,
                debug_info=self.result['debug_info']
            )
        
        # Process each command to add remote prefix if specified
        processed_commands = []
        for cmd in commands_to_execute:
            processed_cmd = self._process_remote_command(cmd)
            processed_commands.append(processed_cmd)
        
        # Execute each command
        self.result['rendered_commands'] = commands_to_execute
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
