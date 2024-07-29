$(document).ready(function () {
    const members = [
	{% assign team = site.profiles | where: "is_alumni", false %}
                {% for member in team %}
               {% assign formatted_thumb = member.thumbnail  %}

                {% assign thumb_size = formatted_thumb.size %}
                {% assign thumb_size_minus_two = thumb_size | minus:2 %}
                {% assign first_char = formatted_thumb | slice: 0 %}
                {% if first_char == "'" %}
                {% assign formatted_thumb = formatted_thumb | slice: 1,thumb_size_minus_two %}
                {% endif %}

                                {% assign path_parts = formatted_thumb | split: '/' %}
                                {% assign filename = path_parts | last %}
                                {% assign directory = formatted_thumb | remove: filename %}
                                {% assign new_filename = 'reduced_' | append: filename | split: '.' | first | append:
                                '.webp' | replace: "'", "\\'" %}
                                {% assign new_url = directory | append: new_filename %}
                    { photo: "{{ new_url }}" }{% if forloop.last == false %},{% endif %}
                {% endfor %}
            ].filter(member => member.photo !== "");
      function getRandomMembers(members, count) {
          let shuffled = members.sort(() => 0.5 - Math.random());
          return shuffled.slice(0, count);
      }
      const randomMembers = getRandomMembers(members, 7);
      const teamSection = $('#teamSection');
      const circles = [
          {class: 'rounded-5  circle-1 rounded-end', member: randomMembers[0]},
          {class: 'rounded-5  circle-2 rounded-start rounded-end', member: randomMembers[1]},
          {class: 'rounded-5  circle-3 rounded-start rounded-end', member: randomMembers[2]},
          {class: 'rounded-5  circle-4 rounded-start', member: randomMembers[5]}
      ];
      circles.forEach(circle => {
          const div = $('<div><div></div>')
              .addClass(`team-circle ${circle.class}`)
              .css('background-image', `url('${circle.member.photo}')`);
          const wrappedDiv = $('<div></div>')
              .addClass('col-3 col-md-2 ')
              .append(div);
          teamSection.append(wrappedDiv);
      });
  });