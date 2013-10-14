# Quick Cheats (make a cheat...):
#
#   - use -n switch for edit or edit-method to not auto-load changed file
#   - edit-method has a -p switch to create a monkey patch temp file. Cool :-)
#   - use `binding.pry` to invoke pry at runtime, for ad hoc debugging, etc.
#   - prevent history from saving at end of session, if you want to clear it:
#        Pry.config.history.should_save = false
#   - regex commands for extension are pretty cool:
#        https://github.com/pry/pry/wiki/Command-system
#
# Some possibilities to check out for debugging with Pry:
#
#   https://github.com/mon-ouie/pry_debug
#   https://github.com/AndrewO/ruby-debug-pry

EDITOR = 'mvim'
Pry.editor = proc { |file, line| "#{EDITOR} #{file} +#{line}" }

if defined?(PryDebugger)
  Pry.commands.alias_command 'c', 'continue'
  Pry.commands.alias_command 's', 'step'
  Pry.commands.alias_command 'n', 'next'
  Pry.commands.alias_command 'f', 'finish'
end
