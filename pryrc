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

Pry.config.commands.import Pry::ExtendedCommands::Experimental
Pry.plugins["doc"].activate!
Pry.plugins["remote"].activate!
Pry.plugins["rails"].activate!
Pry.plugins["nav"].activate!
Pry.plugins["stack_explorer"].activate!
Pry.plugins["vterm_aliases"].activate!
Pry.plugins["gist"].activate!
Pry.plugins["awesome_print"].activate!

# Example of custom prompt mucking
# Pry.config.prompt = proc { |obj, nest_level| "#{obj}:#{obj.instance_eval('_pry_').instance_variable_get('@output_array').count}> " }
# Pry.config.prompt = proc { |obj, nest_level| "#{obj}:#{obj.instance_eval('Pry').class_eval('@current_line')}> " }

require 'rubygems'
begin
  require 'jist'
  require 'interactive_editor'
rescue LoadError => err
  puts err
end

begin
  require 'hirb'

  # Dirty hack to support in-session Hirb.disable/enable
  Hirb::View.instance_eval do
    def enable_output_method
      @output_method = true
      Pry.config.print = proc do |output, value|
        Hirb::View.view_or_page_output(value) || Pry::DEFAULT_PRINT.call(output, value)
      end
    end

    def disable_output_method
      Pry.config.print = proc { |output, value| Pry::DEFAULT_PRINT.call(output, value) }
      @output_method = nil
    end
    def vertical
      Hirb.enable(:output => {"ActiveRecord::Base" => {:class => :auto_table, :options => {:vertical => true}}})
    end

    def horizational
      Hirb.enable(:output => {"ActiveRecord::Base" => {:class => :auto_table, :options => {:vertical => false}}})
    end
  end

  Hirb.enable
rescue LoadError => err
  puts 'no hirb :('
end

begin
  require 'wirble'
  Wirble.init
  Wirble.colorize
rescue
  puts 'no wirble'
end

begin
  require 'awesome_print'
   Pry.config.print = proc { |output, value| Pry::Helpers::BaseHelpers.stagger_output("=> #{value.ai}", output) }
rescue LoadError => err
  puts "no awesome_print :("
end

# Log Rails stuff like SQL/Mongo queries to $stdout if in Rails console
if defined?(Rails) && Rails.respond_to?(:logger)    # Rails 3 style
  require 'logger'
  Rails.logger = Logger.new($stdout)
  def toggle_db_logging
    if $db_logging_enabled
      ActiveRecord::Base.logger = Logger.new(nil) if defined?(ActiveRecord)
      Mongoid.logger = Logger.new(nil) if defined?(Mongoid)
      $db_logging_enabled = false
    else
      ActiveRecord::Base.logger = Rails.logger if defined?(ActiveRecord)
      Mongoid.logger = Rails.logger if defined?(Mongoid)
      $db_logging_enabled = true
    end
  end
  toggle_db_logging
# Rails < 3.0.0
elsif ENV.include?('RAILS_ENV') && !Object.const_defined?('RAILS_DEFAULT_LOGGER')
  require 'logger'
  RAILS_DEFAULT_LOGGER = Logger.new($stdout)
end


# Launch Pry with access to the entire Rails stack.
# If you have Pry in your Gemfile, you can pass: ./script/console --irb=pry instead.
# If you don't, you can load it through the lines below :)
rails = File.join Dir.getwd, 'config', 'environment.rb'

if File.exist?(rails) && ENV['SKIP_RAILS'].nil?
  require rails
  
  if Rails.version[0..0] == "2"
    require 'console_app'
    require 'console_with_helpers'
  elsif Rails.version[0..0] == "3"
    require 'rails/console/app'
    require 'rails/console/helpers'
  else
    warn "[WARN] cannot load Rails console commands (Not on Rails2 or Rails3?)"
  end
end

#
# Random custom commands
#
Pry.commands.command(/!(\d+)/, "Replay a line of history, bash-style", :listing => "!hist") do |id|
  run "history --replay #{id}"
end

# Sed-style substitution for fixes in the current multi-line input buffer
Pry.commands.command(/s\/(.*?)\/(.*?)/) do |source, dest|
  eval_string.gsub!(/#{source}/) { dest }
  run 'show-input'
end

# vim:filetype=ruby
