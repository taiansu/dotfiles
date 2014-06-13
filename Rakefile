require 'rake'

task default: %w[update:async_tasks update:prezto update:finish_msg]

namespace :update do
  multitask async_tasks: %w[homebrew node vim]

  [:homebrew, :node, :prezto, :emacs, :vim].each do |task_name|
    desc "Update #{task_name}"
    task task_name do
      send "update_#{task_name}"
    end
  end

  desc "show a finish message"
  task :finish_msg do
    cmd = cowsay? ? "cowsay" : "print"
    clear_screen
    send "#{cmd}_finish"
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

  def clear_screen
    sh 'clear'
    5.times { puts '' }
  end

  def cowsay?
    (sh "brew -v") && (`brew list cowsay`)
  end

  def print_finish
    puts "====================================================="
    puts "=====    All done! Wish you have a nice day!    ====="
    puts "====================================================="
  end

  def cowsay_finish
    cow_file = %W[bud-frogs bunny default dragon-and-cow hellokitty kitty koala
    luke-koala meow moose satanic sheep small stegosaurus supermilker three-eyes
    turkey turtle tux udder vader vader-koala]

    cow_eye = ["-b", "-d", "-g", "-p", "-s", "-t", "-w", "-y", ""].sample
    cow_cmd = rand(2) > 0.5 ? 'cowsay' : 'cowthink'
    system("fortune | #{cow_cmd} -f #{cow_file.sample} #{cow_eye}")
  end
end
