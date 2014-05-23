require 'rake'

task default: [:morning, :prezto, :finish]

multitask morning: [:homebrew, :node,  :emacs, :vim]

[:homebrew, :node, :prezto, :emacs, :vim].each do |task_name|
  task task_name do
    send "update_#{task_name}"
  end
end

task :finish do
  if (sh "brew -v") && (sh "brew list cowsay")
    sh 'clear'
    5.times do puts '' end
    cow_eye = ["-b", "-d", "-g", "-p", "-s", "-t", "-w", "-y", ""].sample
    cow_cmd = rand(2) > 0.5 ? 'cowsay' : 'cowthink'
    sh "#{cow_cmd} #{cow_eye} 'All done! Wish you have a nice day!'"
  else
    sh 'clear'
    5.times do puts '' end
    print_finish
  end
end

def update_homebrew
  return unless sh "brew -v"
  sh 'brew update'
  sh 'brew upgrade'
  sh 'brew cleanup'
end

def  update_node
  return unless sh "npm -v"
  sh 'npm update -g'
end

def update_prezto
  return unless File.directory? "#{Dir.home}/.zprezto"
  Dir.chdir "#{Dir.home}/.zprezto"
  sh 'git stash -u'
  sh 'git pull'
  sh 'git stash pop'
end

def update_emacs
  return unless File.directory?("#{Dir.home}/.emacs.d")
  return unless sh "cask --version"
  Dir.chdir("#{Dir.home}/.emacs.d")
  sh 'cask update'
end

def update_vim
  vim_update_command = 'vim "+set nomore" "+UpdateActivatedAddons" "+qall"'
  sh vim_update_command
end

def print_finish
  puts "====================================================="
  puts "=====    All done! Wish you have a nice day!    ====="
  puts "====================================================="
end
