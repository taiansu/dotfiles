#!/usr/bin/env ruby
require 'mkmf'

module Morning
  class Updater
    def update_homebrew
      puts 'updating Homebrew...'

      puts `brew update`

      # print 'Would you like to update all Homebrew items? (Y/n) [1]'
      update = true

      # user_input = gets.chomp!
      # 1.downto(0){ |t|
      #   sleep 1
      #   print "\b\b#{t}]"
      # }
      # puts ''
      # update = false if ['n', 'no', 'N'].include? user_input

      upgrade_homebrew if update
    end

    def upgrade_homebrew
      return unless find_executable('brew')
      puts %x(brew upgrade)
      system('brew cleanup')
    end

    def update_node
      return unless find_executable('npm')
      puts 'updating node plugins...'
      %x(npm -g list --depth 0 | grep -v "^/" | cut -f2 -d" " | cut -f1 -d@ | grep -v "^npm$" | xargs npm -g update)
      puts 'updating npm...'
      %x(./npm_updater.sh)
    end

    def update_prezto
      return unless File.directory?("#{Dir.home}/.zprezto")
      puts 'updating prezto...'
      Dir.chdir("#{Dir.home}/.zprezto")
      `git stash -u`
      puts `git pull`
      `git stash pop`
    end

    def update_emacs
      return unless File.directory?("#{Dir.home}/.emacs.d")
      return unless find_executable('cask')
      puts 'updating emacs...'
      Dir.chdir("#{Dir.home}/.emacs.d")
      `cask update`
      `rm -rf mkmf.log`
    end

    def update_vim_plugins
      puts 'updating vim plugins...'
      vim_update_command = 'vim "+set nomore" "+UpdateActivatedAddons" "+qall"'
      exec vim_update_command
    end


    def self.run
      runner = new
      public_instance_methods(false).each do |m|
        runner.send(m)
      end
    end
  end
end

if __FILE__ == $0
  Morning::Updater.run
end

