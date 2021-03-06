#!/usr/bin/env python3.3

from tkinter import *
from tkinter import ttk
import http.client
import json
import urllib.request
import os

def get_pics():

    subs = []

    try:
        subs = subreddits.get().split(',')
        for i in range(0, len(subs)):
            subs[i] = subs[i].strip().lower()
    except:
        print('Problems with button.')

    setup_storage()

    if file_limit.get().isalpha():
        file_limit.set('25')
    elif int(file_limit.get()) <= 0:
        file_limit.set('1')
    elif int(file_limit.get()) > 100:
        file_limit.set('100')

    progress.configure(maximum=(len(subs) * int(file_limit.get())), value=0)
    
    for subreddit in subs:

        print('')
        print('Downloading ' + subreddit + ':')

        r_response = get_reddit_response(subreddit)
        json_dict = json.loads(r_response)

        if subreddit not in store_json:
            store_json[subreddit] = []

        if not os.path.exists('./pics/' + subreddit):
            os.makedirs('./pics/' + subreddit)

        for post in json_dict['data']['children']:
            if not get_image(post, subreddit):
                progress.step()
                main.update_idletasks()
                continue
            else:
                progress.step()
                main.update_idletasks()
                print('Downloaded something.')

    print('Finished')

    #Closing the connections
    d_conn.close()
    t_conn.close()
    i_conn.close()
    conn.close()

    #Storing the updated list of downloaded posts.
    store_file = open('./data.txt', 'w')
    json.dump(store_json, store_file)
    store_file.close()

def setup_storage():
    global store_json

    try:
        store_file = open('./data.txt', 'r')
    except FileNotFoundError:
        new_file = open('./data.txt', 'w')
        new_file.write('{}')
        new_file.close()
        store_file = open('./data.txt', 'r')

    store_json = json.load(store_file)
    store_file.close()

def get_reddit_response(sub):

    
    hdr = {'User-Agent' : 'Get Mah Pics'}
    conn.request('GET', '/r/' + sub + '/.json?limit=' + str(int(file_limit.get())), headers=hdr)
    response = conn.getresponse().readall().decode('utf-8')
    return response

def get_image(post, sub):

    p_data = post['data']

    if p_data['is_self']:
        print('Is Self')
        return False
    
    if p_data['id'] in store_json[sub]:
        print('Already downloaded.')
        return False
    
    if p_data['over_18'] and nsfw_filter.get() == 'True':
        print('Skipping NSFW content.')
        return False

    link = p_data['url']

    #For direct to image links
    if get_file_type(link) in file_types:
        download_image(link, sub, p_data['id'], '')
        return True

    #For Imgur links
    elif p_data['domain'] == 'imgur.com':
        img_id = get_imgur_id(link)

        i_response = get_imgur_response(img_id, 'image')

        if i_response == 'Bad Response':
            return False
        
        ijson_dict = json.loads(i_response)

        if ijson_dict['success']:
            download_image(ijson_dict['data']['link'], sub, p_data['id'], '')
            return True
        elif '/a/' in link:
            ijson_dict = json.loads(get_imgur_response(img_id, 'album'))
            count = 0
            for image in ijson_dict['data']['images']:
                download_image(image['link'], sub, p_data['id'], '-' + str(count))
                count += 1
            return True
        else:
            print('Explosion sauce')

    #For Devianart Links
    elif 'deviantart.com' in p_data['domain']:
        try:
            djson_dict = json.loads(get_deviantart_response(link))
            d_link = djson_dict['url']
            download_image(d_link, sub, p_data['id'], '')
            return True
        except Exception as err:
            print('Problem with ' + link + ' : ' + str(err))

    #For Tumblr Links
    elif 'tumblr.com' in p_data['domain']:
        
        try:
            tjson_dict = json.loads(get_tumblr_response(link))
            post_list = tjson_dict['response']['posts']
            if len(post_list) == 1 and post_list[0]['type'] == 'photo':
                t_post = post_list[0]
                t_photos = t_post['photos']

                if len(t_photos) == 1:
                    download_image(t_photos[0]['alt_sizes'][0]['url'], sub, p_data['id'], '')
                else:
                    count = 0
                    for photo in t_photos:
                        download_image(photo['alt_sizes'][0]['url'], sub, p_data['id'], '-' + str(count))
                        count += 1
                    return True
            else:
                print('Not a Picture Post')
                return False
        except Exception as err:
            print('Problem with ' + link + ' : ' + str(err))

def download_image(link, sub, r_id, num_s):

    store_json[sub].append(r_id)

    try:
        urllib.request.urlretrieve(link, './pics/' + sub + '/' + r_id + num_s + '.' + get_file_type(link))
    except Exception as err:
        print(str(err) + ' with ' + link)

def get_file_type(link):
    file_type = link.split('.')[-1]
    file_type = file_type[:3]
    return file_type

def get_imgur_id(link):
    return link.split('/')[-1]

def get_imgur_response(i_id, i_type):

    global i_conn
    
    iresponse = 'Bad Response'

    ihdr = {'Authorization' : 'Client-ID 454fb76af7e09f2'}

    try:
        i_conn.request('GET', '/3/' + i_type + '/' + i_id + '.json', headers=ihdr)
        iresponse = i_conn.getresponse().readall().decode('utf-8')
    except Exception as err:
        print('Problem with ' + i_id + ': ' + str(err))
        i_conn.close()
        i_conn = http.client.HTTPSConnection('api.imgur.com')

    return iresponse

def get_deviantart_response(link):

    dresponse = 'Bad Response'

    try:
        d_conn.request('GET', '/oembed?url=' + link)
        dresponse = d_conn.getresponse().readall().decode('utf-8')
    except Exception as err:
        print('Problem with ' + link + ' : ' + str(err))

    return dresponse

def get_tumblr_response(link):

    t_response = 'Bad Response'

    api_key = 'dkQxCaFiLnOUGOJVAcpkio0qnYMYOSEfjpWXMw9H5L6HI9Gn1o'

    t_id = get_tumblr_id(link)
    t_hostname = get_tumblr_hostname(link) + '.tumblr.com'

    request = '/v2/blog/' + t_hostname + '/posts?api_key=' + api_key + '&id=' + t_id
    
    try:
        t_conn.request('GET', request)
        t_response = t_conn.getresponse().readall().decode('utf-8')
    except Exception as err:
        print('Problem with ' + link + ' : ' + str(err))

    return t_response
    
def get_tumblr_id(link):
    link_list = link.split('/')
    return link_list[link_list.index('post') + 1]

def get_tumblr_hostname(link):
    link_list = link.split('.')
    host_list = link_list[0].split('/')
    return host_list[-1]

#Connections
conn = http.client.HTTPConnection('www.reddit.com')
i_conn = http.client.HTTPSConnection('api.imgur.com')
d_conn = http.client.HTTPConnection('backend.deviantart.com')
t_conn = http.client.HTTPConnection('api.tumblr.com')

#Other Setup
store_json = json.loads('{}')
file_types = ['jpg', 'gif', 'png']

#Setup GUI
main = Tk()
main.title('Get Mah Pics')

mainframe = ttk.Frame(main)
mainframe.grid(column=0, row=0, sticky=(N, S, E, W))
mainframe.columnconfigure(0, weight=1)
mainframe.rowconfigure(0, weight=1)

subreddits = StringVar()
nsfw_filter = StringVar()
file_limit = StringVar()
file_limit.set('25')

sub_entry = ttk.Entry(mainframe, width=20, textvariable=subreddits)
sub_entry.grid(column=1, row=0, sticky=(W, E))

file_limit_entry = ttk.Entry(mainframe, width=7, textvariable=file_limit)
file_limit_entry.grid(column=1, row=1, sticky=(W,E))

check = ttk.Checkbutton(mainframe, text='NSFW Filter', variable=nsfw_filter, onvalue='True', offvalue='False')
check.grid(column=0, row=2, sticky=(W))
check.state(statespec=['selected'])
nsfw_filter.set('True')

progress = ttk.Progressbar(mainframe, orient='horizontal', length=100, mode='determinate')
progress.grid(column=0, row=4, columnspan=2, sticky=(W,E))

ttk.Label(mainframe, text='Subreddits').grid(column=0, row=0, sticky=(E))
ttk.Button(mainframe, text='Get Your Pics', command=get_pics).grid(column=1, row=2, sticky=(E))
ttk.Label(mainframe, text='Total Posts (Max 100)').grid(column=0, row=1, sticky=(E))

for child in mainframe.winfo_children():
    child.grid_configure(padx=5, pady=5)
sub_entry.focus()

main.mainloop()
