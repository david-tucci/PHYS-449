from bokeh.plotting import figure,show
import matplotlib.pyplot as plt
from tweepy.api import API
import tweepy

seconds = [1,2,3,4,5,6,7,8,9]
data = [3,8,9,3,2,8,0,1,3]

# This is bokeh
# p = figure(title="temp vs seconds",x_axis_label="time",y_axis_label="temp")
# p.line(seconds,data,legend_label="Temp2",line_color="blue")
# show(p)

plt.plot(seconds,data)
plt.xlabel("Time(s)")
plt.ylabel("Temperature(C)")
plot = plt.savefig('plot.png')


CONSUMER_KEY = '1znLOcQw8Pktyczzk8tABdKH1'
CONSUMER_SECRET = '1XhCSPGwFy5Fgk6GOC7LcbGSqSriDY8gqYl8RWm3P3QJvXr0AV'

ACCESS_KEY = '1578097015178907653-M7YcAikx0oi3EsRYhPSw9B62bAqy5A'
ACCESS_SECRET = 'OWtdUxv55nDfd8cz5YvaDMzJFYqtTwWd1i1vZCO91wpRb'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

api = tweepy.API(auth)

# Upload media to Twitter APIv1.1
ret = api.media_upload(filename="plot.png", file=plot)

# Attach media to tweet
api.update_status(media_ids=[ret.media_id_string], status="hello world")

# api.update_status('works?')


