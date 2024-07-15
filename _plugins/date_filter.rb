module Jekyll
  module DateFilter
    require 'date'

    def days_ago(date)
      parsed_date = Date.parse(date.to_s)
      days_diff = (Date.today - parsed_date).to_i

      if days_diff == 1
        "1 day ago"
      elsif days_diff <= 29
        "#{days_diff} days ago"
      else
        parsed_date.strftime("%d %B %Y")
      end
    end
  end
end

Liquid::Template.register_filter(Jekyll::DateFilter)
