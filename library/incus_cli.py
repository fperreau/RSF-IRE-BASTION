#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from collections.abc import Mapping
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
    vars:
        description:
            - Additional variables to expose to Jinja templating
        type: dict
        required: false
        default: {}
    ignore_errors:
        description:
            - Whether to ignore command execution errors
        type: bool
        required: false
        default: false
    debug:
        description:
            - Whether to include the rendered commands in result.stdout
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
            project=dict(type='str', required=False, default=None),
            chdir=dict(type='str', required=False, default=None),
            environment=dict(type='dict', required=False, default={}),
            vars=dict(type='dict', required=False, default={}),
            ignore_errors=dict(type='bool', required=False, default=False),
            debug=dict(type='bool', required=False, default=False),
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
        self.project = self.module.params['project']
        self.chdir = self.module.params['chdir']
        self.environment = self.module.params['environment']
        self.extra_vars = self.module.params['vars']
        self.ignore_errors = self.module.params['ignore_errors']
        self.debug = self.module.params['debug']
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
    
    def _create_jinja_environment(self, loader=None):
        """Create a Jinja2 environment with Ansible-compatible filters."""
        env = Environment(
            loader=loader or BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        filters = {
            'to_json': json.dumps,
            'to_nice_json': lambda x: json.dumps(x, indent=2),
            'bool': bool,
            'int': int,
            'float': float,
            'string': str,
        }

        for name, func in filters.items():
            env.filters[name] = func

        return env

    def _normalize_mapping(self, value):
        """Return a plain dictionary from a mapping-like object."""
        if isinstance(value, Mapping):
            return dict(value)
        return {}

    def _merge_render_variables(self, variables, override_variables=None):
        """Merge a base variable set with explicit render-time overrides."""
        merged = self._normalize_mapping(variables)
        override_map = self._normalize_mapping(override_variables)
        for key, value in override_map.items():
            if value is not None:
                merged[key] = value
        return merged

    def _render_template(self, template_content, variables, override_variables=None):
        """Render a Jinja2 template string with Ansible variables."""
        render_variables = self._merge_render_variables(variables, override_variables)
        try:
            env = self._create_jinja_environment()
            template = env.from_string(template_content)
            return template.render(**render_variables)
        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to render template: {str(e)}",
                error=str(e),
                template=template_content
            )

    def _render_template_file(self, template_path, variables, override_variables=None):
        """Render a Jinja2 template file with Ansible variables."""
        render_variables = self._merge_render_variables(variables, override_variables)
        try:
            template_dir = os.path.dirname(template_path) or '.'
            template_file = os.path.basename(template_path)

            template_content = None
            if os.path.exists(template_path):
                with open(template_path, 'r') as f:
                    template_content = f.read()
                self.result['debug_info']['template_content'] = template_content
                self.result['debug_info']['template_path'] = template_path
                self.result['debug_info']['template_exists'] = True
            else:
                self.result['debug_info']['template_exists'] = False

            env = self._create_jinja_environment(FileSystemLoader(template_dir))
            template = env.get_template(template_file)

            self.result['debug_info']['variables_passed_count'] = len(render_variables)
            self.result['debug_info']['variables_passed_keys'] = list(render_variables.keys())

            rendered = template.render(**render_variables)

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
                available_variables=render_variables,
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
    
    def _get_ansible_variables(self, override_variables=None):
        """Build a merged view of Ansible variables available to the module."""
        variables = {}
        debug_info = {}

        context_vars = self._normalize_mapping(getattr(self.module, 'vars', None) or {})
        if context_vars:
            variables.update(context_vars)
            debug_info['module_vars_found'] = sorted(context_vars.keys())
        else:
            debug_info['module_vars_found'] = []

        module_params = {}
        for param_name, param_value in self.module.params.items():
            if param_name in ('command', 'template', 'vars'):
                continue
            if param_value is not None:
                module_params[param_name] = param_value
                variables[param_name] = param_value

        if module_params:
            debug_info['module_params_found'] = sorted(module_params.keys())

        explicit_vars = self._normalize_mapping(self.extra_vars or {})
        if explicit_vars:
            variables.update(explicit_vars)
            debug_info['extra_vars_found'] = sorted(explicit_vars.keys())
        else:
            debug_info['extra_vars_found'] = []

        host_vars = self._normalize_mapping(getattr(self.module, '_host_vars', None) or {})
        host_vars_added = {k: v for k, v in host_vars.items() if k not in variables}
        if host_vars_added:
            debug_info['host_vars_found'] = sorted(host_vars_added.keys())
            variables.update(host_vars_added)

        group_vars_collection = self._normalize_mapping(getattr(self.module, '_group_vars', None) or {})
        group_vars_added = {}
        if isinstance(getattr(self.module, '_group_vars', None), Mapping):
            for _, vars_dict in self.module._group_vars.items():
                if isinstance(vars_dict, Mapping):
                    for key, value in vars_dict.items():
                        if key not in variables:
                            group_vars_added[key] = value
                            variables[key] = value
        if group_vars_added:
            debug_info['group_vars_found'] = sorted(group_vars_added.keys())

        facts = self._normalize_mapping(getattr(self.module, '_facts', None) or {})
        facts_added = {k: v for k, v in facts.items() if k not in variables}
        if facts_added:
            debug_info['facts_found'] = sorted(facts_added.keys())
            variables.update(facts_added)

        override_map = self._normalize_mapping(override_variables)
        if override_map:
            for key, value in override_map.items():
                if value is not None:
                    variables[key] = value
            debug_info['render_override_vars_found'] = sorted(override_map.keys())
        else:
            debug_info['render_override_vars_found'] = []

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
        # Collect all Ansible variables and module parameters.
        # The precedence is intentionally aligned to a simple Ansible-like model:
        # context vars -> explicit task vars -> module parameters -> explicit render overrides.
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
        self.result['debug_info']['rendered_command_count'] = len(commands_to_execute)
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
        rendered_output = '\n'.join(commands_to_execute)
        command_output = '\n'.join(all_stdout) if self.return_output else ''

        if self.debug:
            if command_output:
                self.result['stdout'] = rendered_output + '\n' + command_output
            else:
                self.result['stdout'] = rendered_output
        else:
            self.result['stdout'] = command_output

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
