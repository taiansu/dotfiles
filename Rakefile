require 'rake'

task default: %w[update:async_tasks_with_commit update:finish_msg]

namespace :update do
  multitask async_tasks_with_commit: %w[homebrew vim_and_commit yarn source spacemacs]
  desc 'Update all without commit plug.vim'
  multitask only: %w[homebrew vim yarn spacemacs asdf]

  [:homebrew, :cask, :npm, :yarn, :vim, :vim_and_commit, :emacs, :spacemacs, :source, :asdf].each do |task_name|
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
    # sh 'brew cleanup'
  end

  def update_cask
    return unless sh 'brew cask --version'
    sh 'brew update'

    ignore_apps = ['microsoft-office']
    outdated_apps = `brew cask outdated | awk '{print $1}'`.split(" ")
    update_apps = outdated_apps - ignore_apps
    sh "brew cask install #{update_apps.join(' ')} --force" unless update_apps.empty?
    sh 'brew cask cleanup'
  end

  def  update_npm
    return unless sh 'npm -v'
    # cd ~/.asdf/installs/nodejs/8.8.1/lib && npm i npm
    sh 'npm set progress=false && npm update -g'
  end

  def update_yarn
    # yarn config set prefix ~/.yarn
    return unless sh 'yarn -v'
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

    return unless File.exist? "#{Dir.home}/.vim/autoload/plug.vim.old"

    Dir.chdir "#{Dir.home}/Projects/vimrc"
    File.delete 'vim/autoload/plug.vim.old'
  end

  def update_vim_and_commit
    update_vim

    return unless File.exist? "#{Dir.home}/.vim/autoload/plug.vim.old"

    Dir.chdir "#{Dir.home}/Projects/vimrc"
    File.delete 'vim/autoload/plug.vim.old'
    sh 'git add vim/autoload && git commit -m "update plug.vim"'
  end

  def update_source
    %w(otp elixir dialyxir phoenix).each do |source|
      puts "Fetching #{source}..."
      Dir.chdir("#{Dir.home}/Projects/source/#{source}")
      puts "#{Dir.pwd}"
      sh 'git fetch && git pull'
      if source == "dialyxir"
        sh 'MIX_ENV=prod mix do compile, archive.build, archive.install --force, dialyzer --plt --no-warn'
      end
      Dir.chdir("#{Dir.home}")
    end
  end

  def update_asdf
    return unless sh 'asdf --verson'

    sh 'asdf update'
    sh 'asdf plugin-update --all'
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

namespace :git do
  desc 'Git pull all sub-directory'
  task :pull_all do
    dir = ARGV[1]
    Dir.chdir("#{dir}")

    Dir.glob("*/").each do |d|
      Dir.chdir("#{Dir.pwd}/#{d}")
      p "=== Pulling: #{Dir.pwd} ==="
      sh 'git stash -u'
      sh 'git checkout master'
      sh 'git fetch && git pull'
      Dir.chdir("../")
    end
  end
end
