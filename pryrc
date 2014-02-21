EDITOR = 'mvim'
Pry.editor = proc { |file, line| "#{EDITOR} #{file} +#{line}" }
