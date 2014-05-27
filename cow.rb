items = items.each do |item|
  system("cowsay -f #{item} hummmm")
  sleep(0.5)
end
