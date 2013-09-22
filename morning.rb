#!/usr/bin/env ruby

def update_homebrew
  puts 'updating Homebrew...'

  puts `brew update`

  print 'Would you like to update all Homebrew items? (Y/n) [8]'
  update = true

  # user_input = gets.chomp!
  8.downto(0){ |t|
    sleep 1
    print "\b\b#{t}]"
  }
  puts ''
  # update = false if ['n', 'no', 'N'].include? user_input

  upgrade_homebrew if update
end

def upgrade_homebrew
  puts 'upgrading Homebrew...'
  `brew upgrade`
  `brew cleanup`
end

def update_node
  puts 'updating node plugins...'
  `npm update -g`
end

def update_vim_plugins
  puts 'updating vim plugins...'
  puts `vim -s ~/Code/vimrc/update_plugins.vim`
end

def update_prezto
  puts 'updating prezto...'
  Dir.chdir("#{Dir.home}/.zprezto")
  `git stash -u`
  puts `git pull`
  `git stash pop`
end

if __FILE__ == $0
  ['homebrew', 'node', 'vim_plugins', 'prezto'].each do |command|
    send("update_#{command}")
  end
end

