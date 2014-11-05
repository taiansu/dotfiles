require 'fileutils'
Dir.glob("#{Dir.home}/.dotfiles/zsh_configs/*").each do |file|
  FileUtils.ln_s file, "#{Dir.home}/.#{File.basename(file)}"
end

FileUtils.ln_s "#{Dir.home}/.dotfiles/zpreto/prompt_midnight_rain_setup",
               "#{Dir.home}/.zpreto/modules/prompt/finctions/prompt_midnight_rain_setup"
