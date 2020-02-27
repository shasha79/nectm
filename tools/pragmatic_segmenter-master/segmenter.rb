require "pragmatic_segmenter"

lang = ARGV[0]
text = ARGV[1] #STDIN.gets

#text = "Hello world. My name is Mr. Smith. I work for the U.S. Government and I live in the U.S. I live in New York."
ps = PragmaticSegmenter::Segmenter.new(text: text, language: lang)
puts ps.segment
