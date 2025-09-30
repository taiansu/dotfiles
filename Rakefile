require 'mkmf'
require 'rake'

task default: %w[update:all_tasks update:finish_msg]

namespace :update do # rubocop: disable BlockLength
  # multitask async_tasks: %w[homebrew vim]
  # task tasks_by_step: %w[async_tasks source]
  multitask all_tasks: %w[homebrew vim]

  %i[homebrew cask npm yarn vim source mise ai].each do |task_name| # rubocop: disable LineLength
    desc "Update #{task_name}"
    task task_name do
      send "update_#{task_name}"
    end
  end

  desc 'show a finish message'
  task :finish_msg do
    cmd = pick_printer(['pokemonsay', 'cowsay'])
    clear_screen
    send cmd.to_s
    # system 'All updates are complete, we are good to go.' if osx?
  end
end

namespace :git do
  desc 'Git pull all sub-directory'
  task :pull_all do
    dir = ARGV[1]
    Dir.chdir(dir.to_s)

    Dir.glob('*/').each do |d|
      Dir.chdir("#{Dir.pwd}/#{d}")
      p "=== Pulling: #{Dir.pwd} ==="
      sh 'git stash -u'
      sh 'git checkout master'
      sh 'git fetch && git pull'
      Dir.chdir('../')
    end
  end
end

private

def update_homebrew
  return unless find_executable 'brew'

  sh 'brew update'
  sh 'brew upgrade'
rescue StandardError => e
  p e
  0
end

def update_cask
  return unless find_executable 'brew'

  sh 'brew update'
  ignore_apps = ['microsoft-office']
  outdated_apps = `brew cask outdated | awk '{print $1}'`.split(' ')
  update_apps = outdated_apps - ignore_apps
  sh "brew cask install #{update_apps.join(' ')} --force" unless update_apps.empty? # rubocop: disable LineLength
end

def update_npm
  return unless find_executable 'npm'

  sh 'npm set progress=false && npm update -g'
end

def update_yarn
  # yarn config set prefix ~/.yarn
  return unless find_executable 'yarn'

  sh 'yarn global upgrade --all'
end

def update_vim
  [
    'nvim --headless "+Lazy! sync" "+qa"',
    'nvim --headless +MasonUpdate +qa',
  ].each { |cmd| sh cmd }
end

def update_source
  %w[otp elixir phoenix ex_doc ecto].each do |source|
    puts "Fetching #{source}..."
    dir = "#{Dir.home}/Projects/source/#{source}"
    git_pull(dir) if Dir.exist?(dir)
  end
end

def git_pull(dir)
  Dir.chdir(dir)
  stdout = `git stash -u`
  has_stash = stdout !~ /No local changes to save/ && stdout !~ /沒有要儲存的本機修改/
  sh 'git pull && git gc'
  sh 'git stash pop' if has_stash
end

def update_mise
  return unless find_executable 'mise'

  sh 'mise self-update'
  sh 'mise plugin update --all'
end

def update_ai
  sh 'claude update'
  sh 'npm update -g @google/gemini-cli'
  sh 'npm update -g @openai/codex'
end

def clear_screen
  sh 'clear'
  5.times { puts '' }
end

def cmd_exist?(cmd)
  (sh 'brew -v') && `brew list #{cmd}`
end

def pick_printer(cmds)
  return "print_finish" unless `brew -v`

  cmds.each do |cmd|
    return "#{cmd}_finish" if `brew list #{cmd}`
  end

  "print_finish"
end

def print_finish
  puts '====================================================='
  puts '=====    All done! Wish you have a nice day!    ====='
  puts '====================================================='
end

def cowsay_finish
  cow_file = %w[bud-frogs bunny default dragon-and-cow hellokitty kitty
                koala luke-koala meow moose satanic sheep small stegosaurus
                three-eyes turkey turtle tux udder vader vader-koala]

  cow_eye = ['-b', '-d', '-g', '-p', '-s', '-t', '-w', '-y', ''].sample
  cow_cmd = rand(2) > 0.5 ? 'cowsay' : 'cowthink'
  system("fortune | #{cow_cmd} -f #{cow_file.sample} #{cow_eye}")
end

def pokemonsay_finish
  system("fortune | pokemonsay")
end

def osx?
  (/darwin/ =~ RUBY_PLATFORM) != nil
end

