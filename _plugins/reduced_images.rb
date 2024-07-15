module Jekyll
  module ThumbnailFilter
    def reduced(input)
      path_parts = File.split(input)
	  directory = path_parts[0]
	  filename = path_parts[1]

  # Add "reduced_" prefix to the filename and change its extension to .webp
	  new_filename = "reduced_" + File.basename(filename, ".*") + ".webp"

  # Construct the new URL
	  new_url = File.join("/", directory, new_filename)
  
	  new_url
	end
  end
end

Liquid::Template.register_filter(Jekyll::ThumbnailFilter)
