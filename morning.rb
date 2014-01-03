#!/usr/bin/env ruby

module Morning
  class Updater
    def update_homebrew
      puts 'updating Homebrew...'

      puts `brew update`

      print 'Would you like to update all Homebrew items? (Y/n) [1]'
      update = true

      # user_input = gets.chomp!
      1.downto(0){ |t|
        sleep 1
        print "\b\b#{t}]"
      }
      puts ''
      # update = false if ['n', 'no', 'N'].include? user_input

      upgrade_homebrew if update
    end

    def upgrade_homebrew
      puts 'upgrading Homebrew...'
      puts %x(brew upgrade)
      system('brew cleanup')
    end

    def update_node
      puts 'updating node plugins...'
      %x(npm update -g)
    end

    def update_vim_plugins
      vim_location = "~/Code/vim_tsu/update_plugins.vim"
      puts 'updating vim plugins...'
      puts `vim +BundleInstall +qall`
    end

    def update_prezto
      puts 'updating prezto...'
      Dir.chdir("#{Dir.home}/.zprezto")
      `git stash -u`
      puts `git pull`
      `git stash pop`
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

