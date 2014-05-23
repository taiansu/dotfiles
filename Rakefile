require 'rake'
require 'rake/clean'

task default: [:morning, :update_prezto, :finish]

multitask morning: [:update_homebrew, :update_node,  :update_emacs, :update_vim]

task :update_homebrew do
  return unless sh "brew -v"
  sh 'brew update'
  sh 'brew upgrade'
  sh 'brew cleanup'
end

task :update_node do
  return unless sh "npm -v"
  sh 'npm update -g'
end

task :update_prezto do
  return unless File.directory? "#{Dir.home}/.zprezto"
  Dir.chdir "#{Dir.home}/.zprezto"
  sh 'git stash -u'
  sh 'git pull'
  sh 'git stash pop'
end

task :update_emacs do
  return unless File.directory?("#{Dir.home}/.emacs.d")
  return unless sh "cask --version"
  Dir.chdir("#{Dir.home}/.emacs.d")
  sh 'cask update'
end

task :update_vim do
  vim_update_command = 'vim "+set nomore" "+UpdateActivatedAddons" "+qall"'
  sh vim_update_command
end

task :finish do
  puts "============================================="
  puts "=====All done! Wish you have a nice day!====="
  puts "============================================="
end
