from imhotep.tools import Tool
from collections import defaultdict
import os
import re
import logging

log = logging.getLogger(__name__)

class PyLint(Tool):
    response_format = re.compile(r'(?P<filename>.*):(?P<line_num>\d+):'
                                 '(?P<message>.*)')
    pylintrc_filename = 'pylint.rcfile'

    def get_file_extensions(self):
        return ['.py']

    def process_line(self, dirname, line):
        match = self.response_format.search(line)
        if match is not None:
            if len(self.filenames) != 0:
                if match.group('filename') not in self.filenames:
                    return
            filename, line, messages = match.groups()
            # If you run pylint on /foo/bar/baz and you are in the /foo/bar
            # directory, it will spit out paths that look like: ./baz To fix
            # this, we run it through `os.path.abspath` which will give it a
            # full, absolute path.
            filename = os.path.abspath(filename)
            return filename, line, messages

    def get_command(self, dirname, **kwargs):
        cmd = 'pylint --output-format=parseable -rn'
        if os.path.exists(os.path.join(dirname, self.pylintrc_filename)):
            cmd += " --rcfile=%s" % os.path.join(
                dirname, self.pylintrc_filename)
        return cmd

    def invoke(self, dirname, filenames=set(), linter_configs=set()):
        """
        Main entrypoint for all plugins.

        Returns results in the format of:

        {'filename': {
          'line_number': [
            'error1',
            'error2'
            ]
          }
        }

        imhotep pylint Appd changes: changed the algorithm to find files to
        focus only on files that we can tell have changed.
        The rest of the code is a copy of the basic invoke
        from imhotep base project.

        """
        retval = defaultdict(lambda: defaultdict(list))
        extensions = ' -o '.join(['-name "*%s"' % ext for ext in
                                  self.get_file_extensions()])
        log.debug("Here's the files passed in: %s", filenames)
        for filename in filenames:
            cmd = 'find %s/%s | xargs %s' % (
                dirname, filename, self.get_command(
                    dirname,
                    linter_configs=linter_configs))
            log.debug("cmd = %s", cmd)
            result = self.executor(cmd)
            for line in result.split('\n'):
                output = self.process_line(dirname, line)
                if output is not None:
                    filename, lineno, messages = output
                    if filename.startswith(dirname):
                        filename = filename[len(dirname) + 1:]
                    retval[filename][lineno].append(messages)
        return retval