require 'rake'

task default: %w[update:node update:async_tasks_with_commit update:finish_msg]
task just_update: %w[update:node  update:async_tasks_without_commit update:finish_msg]

namespace :update do
  multitask async_tasks_with_commit: %w[homebrew vim_and_commit npm]
  multitask async_tasks_without_commit: %w[homebrew vim npm]

  [:homebrew, :node, :npm, :vim, :vim_and_commit, :emacs].each do |task_name|
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
    system "All updates are complete, we are good to go now." if RUBY_PLATFORM =~ /darwin/
  end

  def update_homebrew
    return unless sh "brew -v"
    sh 'brew update'
    sh 'brew upgrade'
    sh 'brew cleanup'
    sh 'brew cask cleanup'
  end

  def update_node
    sh './update_node.sh'
  end

  def  update_npm
    return unless sh "npm -v"
    sh 'npm set progress=false && npm update -g'
  end

  def update_emacs
    return unless File.directory?("#{Dir.home}/.emacs.d")
    return unless sh "cask --version"
    # Dir.chdir("#{Dir.home}/.emacs.d")
    # sh 'cask upgrade'
    # sh 'cask update'
  end

  def update_vim
    vim_update_command = 'mvim -v "+set nomore" "+PlugUpgrade" "+PlugUpdate" "+qall"'
    sh vim_update_command
  end

  def update_vim_and_commit
    update_vim

    if File.exist? "#{Dir.home}/.vim/autoload/plug.vim.old"
      Dir.chdir "#{Dir.home}/Projects/vim_tsu"
      File.delete 'vim/autoload/plug.vim.old'
      sh 'git add vim/autoload && git commit -m "update plug.vim"'
    end
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

  private
  def osx?
    (/darwin/ =~ RUBY_PLATFORM) != nil
  end
end
