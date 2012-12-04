require 'rubygems'
require 'wirble'
require 'hirb'
require 'ap'

Wirble.init
Wirble.colorize

alias q exit

@recent_files = []
def fl(file_name)
  file_name = file_name.to_s if file_name.class.eql? Symbol
  file_name += '.rb' unless file_name =~ /\.rb/
  @recent_files.delete file_name if @recent_files.include? file_name
  @recent_files << file_name
  load_last_file
end

def rl!
  load_all_files
end

def rl
  load_last_file
end

# More than one way to do this
# Commented is the ruby way
# uncommentted is my preferred way
def ls
  #entries = instance_eval("Dir.entries(File.dirname(__FILE__))")
  #(entries - ["..", "."]).reverse
  %x{ls}.split("\n")
end

private

def load_all_files
  @recent_files.each do |file|
    load "#{file}"
  end
  "Done!"
end

def load_last_file
  load "#{@recent_files.last}"
end

