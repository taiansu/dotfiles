require 'rake'

task default: %w[update:async_tasks_with_commit update:finish_msg]

namespace :update do
  multitask async_tasks_with_commit: %w[homebrew vim_and_commit yarn source spacemacs]
  desc 'Update all without commit plug.vim'
  multitask only: %w[homebrew vim yarn spacemacs]

  [:homebrew, :node, :npm, :yarn, :vim, :vim_and_commit, :emacs, :spacemacs, :source].each do |task_name|
    desc "Update #{task_name}"
    task task_name do
      send "update_#{task_name}"
    end
  end

  desc 'show a finish message'
  task :finish_msg do
    cmd = cowsay? ? 'cowsay' : 'print'
    clear_screen
    send "#{cmd}_finish"
    system 'All updates are complete, we are good to go.' if osx?
  end

  def update_homebrew
    return unless sh 'brew -v'
    sh 'brew update'
    sh 'brew upgrade'
    sh 'brew cleanup'
    sh 'brew cask cleanup'
  end

  def update_node
    sh './update_node.sh'
  end

  def  update_npm
    return unless sh 'npm -v'
    sh 'npm set progress=false && npm update -g'
  end

  def update_yarn
    sh 'yarn global upgrade'
  end

  def update_spacemacs
    spacemacs_dir = "#{Dir.home}/Projects/spacemacs"
    return unless File.directory?(spacemacs_dir)
    Dir.chdir(spacemacs_dir)
    sh 'git fetch && git pull'
  end

  def update_vim
    vim_update = 'nvim "+set nomore" "+PlugUpgrade" "+PlugUpdate" "+UpdateRemotePlugin" "+qall"'
    sh vim_update
  end

  def update_vim_and_commit
    update_vim

    return unless File.exist? "#{Dir.home}/.vim/autoload/plug.vim.old"

    Dir.chdir "#{Dir.home}/Projects/vimrc"
    File.delete 'vim/autoload/plug.vim.old'
    sh 'git add vim/autoload && git commit -m "update plug.vim"'
  end

  def update_source
    %w(otp elixir dialyxir credo).each do |source|
      puts "Fetching #{source}..."
      Dir.chdir("#{Dir.home}/Projects/source/#{source}")
      sh 'git fetch && git pull'
      if source == "dialyxir"
        sh 'MIX_ENV=prod mix do compile, archive.build, archive.install --force, dialyzer --plt --no-warn'
      end
    end
  end

  def clear_screen
    sh 'clear'
    5.times { puts '' }
  end

  def cowsay?
    (sh 'brew -v') && `brew list cowsay`
  end

  def print_finish
    puts '====================================================='
    puts '=====    All done! Wish you have a nice day!    ====='
    puts '====================================================='
  end

  def cowsay_finish
    cow_file = %w(bud-frogs bunny default dragon-and-cow hellokitty kitty
                  koala luke-koala meow moose satanic sheep small stegosaurus
                  three-eyes turkey turtle tux udder vader vader-koala)

    cow_eye = ['-b', '-d', '-g', '-p', '-s', '-t', '-w', '-y', ''].sample
    cow_cmd = rand(2) > 0.5 ? 'cowsay' : 'cowthink'
    system("fortune | #{cow_cmd} -f #{cow_file.sample} #{cow_eye}")
  end

  private

  def osx?
    (/darwin/ =~ RUBY_PLATFORM) != nil
  end
end
