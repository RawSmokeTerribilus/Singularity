        ##---------THE LAST DIGITAL UNDERGROUND PRESENTS-------##
        ##                                                     ##
        ##                 Special Recruitment :)              ##
        ##          @ https://TheLDU.to/application            ##
        ##                                                     ##
        ##                              Ref: Uploadrr by CvT   ##
        ##-----------------------------------------------------##

config = {
    'version': '1.0.7',
	
    "DEFAULT" : {

        "tmdb_api" : "TMDB_API_KEY", ## REQUIRED 
        "imgbb_api" : "imgbb_API_KEY", ## Fastest but api rate limits + DMCA Takedowns
        "ptpimg_api" : "ptpimg_API_KEY", 
        "lensdump_api" : "lensdump_API_KEY", ## https://lensdump.com/settings/api 
        "ptscreens_api" : "ptscreens_API_KEY", ## https://ptscreens.com/settings/api
        "oeimg_api" : "oeimg_API_KEY", ## https://imgoe.download/settings/api

        # Order of image hosts, and backup image hosts
        "img_host_1": "imgbb",
        "img_host_2": "ptpimg",
        "img_host_3": "imgbox",
	    "img_host_4": "pixhost",
        "img_host_5": "lensdump",
        "img_host_6": "ptscreens",
        "img_host_7": "oeimg",

        "screens" : "6",
        "img_size" : "500",  #Size in Description [img=500]
        "optimize_images" : True,  # Lossless PNG Compression (True/False)
	    #"inline_imgs": 3, #Uncomment and use this if you want to insert a line break after X images in description
        "add_logo" : False, # Adds Logo as header
        #"logo_size": 400, #Uncomment and choose a logo size. Defauts to 420 if nothing is set. Recomended range 300-500
        "add_trailer" : True, # Adds Movie Trailer (Skips TV as season specifier not supported)

        ### GOLBAL SIGNATURES ###
        "use_global_sigs": True, # If False it will use your tracker signatures       
        "global_sig": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]", 
        "global_anon_sig": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
        "global_pr_sig": "\n[center][size=6][b]Personal Release[/b][/size][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]", #personal realease signature
        "global_anon_pr_sig": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	 

        # The name of your default torrent client, set in the torrent client sections below
        "default_torrent_client" : "Client1",

        # Play the bell sound effect when asking for confirmation
        "sfx_on_prompt" : True,
    },

    "AUTO" :{  ####### AUTO / POWER USER SETTINGS ########
        "description_folder" : None, # Specify a "path/to/folder" to find description files that auto-add. For use with -aid 
                                     # Expected format: Movie is: "Nineteen.Eighty.Four.1984.Hybrid.1080p.BluRay.REMUX.AVC.DTS-HD.MA.1.0-EPSiLON.mkv" 
                                     #       .txt file should be: "Nineteen.Eighty.Four.1984.Hybrid.1080p.BluRay.REMUX.AVC.DTS-HD.MA.1.0-EPSiLON.txt"
                                     # For TV Season use `Folder.Name.of.Season.txt`

        "delay" : 0, # Number of Seconds to delay bewteen your queued uploads 600 = 10 Min delay
        "size_tolerance" : 1, # Dupe filtering. This is the size fuzz in percentage if less than 1% diffrence than it cacultates diffrence based on name.       
        "dupe_similarity" : 80, # Name dupe filtering. 100 would only filter out an exact match
    },         ###########################################   

    "TRACKERS" : {
        # Which trackers do you want to upload to? Ex: "LDU, RF, ULCX",
        "default_trackers" : "LDU",

        "LDU" : {
            "api_key" : "LDU_API_KEY",
            "announce_url" : "https://theldu.to/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED LDU FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]", #Only used if "use_global_sigs" : False,
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]", #Only used if "use_global_sigs" : False, AND your uploading as "anon" : True, or passing -a at upload
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED LDU FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]", #Only used if "use_global_sigs" : False, AND -pr
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]", #Only used if "use_global_sigs" : False, AND your uploading as "anon" : True, or passing -a with -pr at upload
            #"qbit_tag": "LDU", #Uncomment and add tag, for auto tagging torrent injection for this tracker
            },   

        "ACM" :{
            "api_key" : "ACM_API_KEY",
            "announce_url" : "https://asiancinema.me/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED ACM FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",          
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED ACM FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "ACM",
            ### FOR INTERNAL USE ONLY: ###
            # "internal" : True,
            # "internal_groups" : ["What", "Internal", "Groups", "Are", "You", "In"],

        },

        "AITHER" :{
            "api_key" : "AITHER_API_KEY",
            "announce_url" : "https://aither.cc/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED AITHER FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]", 
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED AITHER FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "AITHER",		
        },

        "ANT" :{
            "api_key" : "ANT_API_KEY",
            "announce_url" : "https://anthelion.me/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED ANT FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED ANT FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "",		
        },

    "AR": {
            "username": "Username",
            "password": "Password",
            "announce_url": "http://tracker.alpharatio.cc:2710/Custom_Announce_URL/announce",
            #"qbit_tag": "AR",
        },

        "BHD" : {
            "api_key" : "BHD_API_KEY",
            "announce_url" : "https://beyond-hd.me/announce/Custom_Announce_URL",
            "draft_default" : True,
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED BHD FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED BHD FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "BHD",		
        },
        "BHDTV": {
            "api_key": "found under https://www.bit-hdtv.com/my.php",
            "announce_url": "https://trackerr.bit-hdtv.com/announce",
            #passkey found under https://www.bit-hdtv.com/my.php
            "my_announce_url": "https://trackerr.bit-hdtv.com/passkey/announce",
            "anon" : False,
            #"qbit_tag": "BHDTV",
        },   

        "BLU" : {
            "useAPI" : False, # Set to True if using BLU
            "api_key" : "BLU_API_KEY",
            "announce_url" : "https://blutopia.cc/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED BLU FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED BLU FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "BLU",		
        },

        "CBR" : {
            "api_key" : "CBR_API_KEY",
            "announce_url" : "https://capybarabr.com/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "[url=https://codeberg.org/CvT/Uploadrr][img=69]https://capybarabr.com/img/capybara.svg[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n [center][url=https://codeberg.org/CvT/Uploadrr][img=69]https://capybarabr.com/img/capybara.svg[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "CBR",		
        },

        "EMU" :{
            "api_key" : "EMU_API_KEY",
            "announce_url" : "https://emuwarez.it/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]", 
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "EMU",		
        },


        "FNP" : {
            "api_key" : "FNP_API_KEY",
            "announce_url" : "https://fearnopeer.com/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED FNP FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",    
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED FNP FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "FnP",		
            }, 

        "FL": {
            "username": "FL_Username",
            "password": "FL_Password",
            "announce_url" : "",
            "uploader_name": "",
            "anon": False,
            #"qbit_tag": "FL",
        },

        "HDB" : {
            "api_key" : "HDB_API_KEY",
            "announce_url" : "https://hdbits.org/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED HDB FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",       
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED HBD FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "HDB",		
            }, 

        "HDT" : {
            "username" : "username",
            "password" : "password",
            "my_announce_url": "https://hdts-announce.ru/announce.php?pid=<PASS_KEY/PID>",
            "anon" : False,
            "announce_url" : "https://hdts-announce.ru/announce.php", #DO NOT EDIT THIS LINE
            #"qbit_tag": "HDT",
        },

        "HP" :{
            "api_key" : "HP_API_KEY",
            "announce_url" : "https://hidden-palace.net/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED HP FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",      
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED HP FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",		
            #"qbit_tag": "HP",
        },

        "HHD" : {
            "api_key" : "HHD_API_KEY",
            "announce_url" : "https://homiehelpdesk.net/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][size=7][b]PLEASE SEED HOMIES[/b][/size][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "HHD",	
        },


        "HUNO" : {
            "api_key" : "HUNO_API_KEY",
            "announce_url" : "https://hawke.uno/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED HUNO FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED HUNO[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "HUNO",	
        },

        "ITA" : {
            "api_key" : "ITA_API_KEY",
            "announce_url" : "https://itatorrents.xyz/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED ITATorrents[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
	        "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED ITATorrents[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
	        "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "ITA",	
            }, 

        "JPTV" : {
            "api_key" : "JPTV_API_KEY",
            "announce_url" : "https://jptv.club/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED JPTV FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
	        "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED JPTV FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
	        "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "JPTV",	
            }, 

        "LCD" : {
            "api_key" : "LCD_API_KEY",
            "announce_url" : "https://locadora.cc/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED LCD FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED LCD FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "LCD",			
        },

        "LST" : {
            "api_key" : "LST_API_KEY",
            "announce_url" : "https://lst.gg/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED LST FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",     
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED LST FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "LST",	
        },

        "LT" : {
            "api_key" : "LT_API_KEY",
            "announce_url" : "https://lat-team.com/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED LAT-Team[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED LAT-Team[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "LT",		
        },
	       
        "MB": {
                "api_key": "MB_API_KEY",
                "announce_url": "https://malayabits.cc/announce/Custom_Announce_URL",
                "anon": False,
            "signature" : "\n[center][b]PLEASE SEED MalayaBits[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED MalayaBits[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "",
        },
	
        "MTV": {
            'api_key' : 'Get_from_security_page',
            'username' : '<USERNAME>',
            'password' : '<PASSWORD>',
            'announce_url' : "get from https://www.morethantv.me/upload.php",
            'anon' : False,
            # 'otp_uri' : 'OTP URI, read the following for more information https://github.com/google/google-authenticator/wiki/Key-Uri-Format'
            #"qbit_tag": "",
        },

        "NBL" : {
            "api_key" : "NBL_API_KEY",
            "announce_url" : "https://nebulance.io/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED Nebulance FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]", 
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED Nebulance[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "NBL",		
        },

        "OE" : {
            "api_key" : "OE_API_KEY",
            "announce_url" : "https://onlyencodes.cc/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED OnlyEncodes FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",     
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED OE FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "OE",			
            },

        "OINK" : {
            "api_key" : "OiNK_API_KEY",
            "announce_url" : "https://yoinked.org/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED YOiNKED FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",     
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "YOiNKED",	
            },            

        "OTW" : {
            "api_key" : "OTW_API_KEY",
            "announce_url" : "https://oldtoons.world/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED OldToons FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",     
            "pr_signature": "\n [center]PERSONAL RELEASE[/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "OTW",	
            },

        "PSS" :{
            "api_key" : "PSS_API_KEY",
            "announce_url" : "https://privatesilverscreen.cc/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED PrivateSilverScreen FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "PSS",	
        },

        "PTER" : {
            "passkey":'passkey',
            "img_rehost" : False,
            "username" : "",
            "password" : "",
            "ptgen_api": "",
            "anon": False,
            #"qbit_tag": "PTER",
        },

        "PTP" : {
            "useAPI" : False, # Set to True if using PTP
            "add_web_source_to_desc" : True,
            "ApiUser" : "PTP_API_USER",
            "ApiKey" : 'PTP_API_KEY',
            "username" : "",
            "password" : "",
            "announce_url" : ""
            #"qbit_tag": "PTP",
        },

        "PTT" :{
            "api_key" : "PTT_API_KEY",
            "announce_url" : "https://polishtorrent.top/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED PolishTorrent FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED PTT FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",	
            #"qbit_tag": "PTT",	
        },

        "R4E" :{
            "api_key" : "R4E_API_KEY",
            "announce_url" : "https://racing4everyone.eu/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED Racing4Everyone FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED R4E FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "R4E",		
        },

        "RF" : {
            "api_key" : "RF_API_KEY",
            "announce_url" : "https://reelflix.xyz/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED ReelFliX FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED RF FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "RF",		
        },

        "RHD" : {
            "api_key" : "RHD_API_KEY",
            "announce_url" : "https://r0k3t.li/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED RocketHD[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "RHD",		
        },

        "RTF": {
            "api_key": "get_it_by_running_/api/ _login_command_from_ https://retroflix.club/api/doc",
            "announce_url": "get_from_upload_page",
            # "tag": "RetroFlix, nd",
            "anon": False,
            "signature" : "\n[center][b]PLEASE SEED RetroFlix FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",    
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED RTF FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "RTF",		
        },

        "SHRI": {
            "api_key": "ShareIsland_API_KEY",
            "announce_url": "https://shareisland.org/announce/Custom_Announce_URL",
            "anon": False,
            "signature" : "\n[center][b]PLEASE SEED ShareIsland[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",    
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED ShareIsland[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "SHRI",		
        },

        "SN": {
            "api_key": "SN_API_KEY",
            "announce_url": "https://tracker.swarmazon.club:8443/<YOUR_PASSKEY>/announce",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED Swarmazon[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]", 
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED Swarmazon[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "SN",		
        },

        "SP": {
            "api_key": "SeedPool_API_KEY",
            "announce_url": "https://seedpool.org/announce/Custom_Announce_URL",
            "anon": False,
            "signature" : "\n[center][b]PLEASE SEED[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",    
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "SP",		
        },

        "THR" : {
            "username" : "username",
            "password" : "password",
            "img_api" : "get_this_from_the_forum_post",
            "announce_url" : "http://www.torrenthr.org/announce.php?passkey=yourpasskeyhere",
            "pronfo_api_key" : "pronfo_API_KEY",
            "pronfo_theme" : "pronfo theme code",
            "pronfo_rapi_id" : "pronfo remote api id",
            "anon" : False,
            #"qbit_tag": "THR",
        },

        "TL": {
            "announce_key": "TL_announce_key",
            #"qbit_tag": "TL",
        },

        "TLZ": {
            "api_key": "TLZ_API_KEY",
            "announce_url": "https://tlzdigital.com/announce/Custom_Announce_URL",
            "anon": False,
            "signature" : "\n[center][b]PLEASE SEED TLZ[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",    
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED TLZ[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "TLZ",		
        },

    	'TOCA' : {
	    'api_key' : 'TOCA_API_KEY',
	    'announce_url' : 'https://tocashare.com/announce/Custom_Announce_URL',
	    'anon' : False,
	    'signature' : '\n[center][b]PLEASE SEED TOCA SHARE[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]',
	    'anon_signature' : '\n[center][size=6]we are anonymous[/size][/center]',
	    "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED TOCA SHARE[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
	    "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
        #"qbit_tag": "TOCA",		
	},
    	'TTR' : {
	    'api_key' : 'TTR_API_KEY',
	    'announce_url' : 'https://torrenteros.org/announce/Custom_Announce_URL',
	    'anon' : False,
	    'signature' : '\n[center][b]PLEASE SEED TorrentEros[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]',
	    'anon_signature' : '\n[center][size=6]we are anonymous[/size][/center]',
	    "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED TorrentEros[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
	    "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
        #"qbit_tag": "TTR",		
	},
	    
        "ULCX" : {
            "api_key" : "ULCX_API_KEY",
            "announce_url" : "https://upload.cx/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED ULCX FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",   
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED ULCX FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "ULCX",		
        },

        "UTP" : {
            "api_key" : "UTP_API_KEY",
            "announce_url" : "https://utp.to/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED UTP FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED UTP FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "UTP",		
        },	
    
        "YU" : {
            "api_key" : "YU_API_KEY",
            "announce_url" : "https://yu-scene.net/announce/Custom_Announce_URL",
            "anon" : False,
            "signature" : "\n[center][b]PLEASE SEED YU-SCENE FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_signature" : "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",  
            "pr_signature": "\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \n[center][b]PLEASE SEED YU-SCENE FAMILY[/b][/center]\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
            "anon_pr_signature": "\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]",
            #"qbit_tag": "YU-Scene",		
        },	

        "MANUAL" : {
            # Uncomment and replace link with filebrowser (https://github.com/filebrowser/filebrowser) link to the Uploadrr directory, this will link to your filebrowser instead of uploading to uguu.se
            # "filebrowser" : "https://domain.tld/filebrowser/files/Uploadrr/"
        },
    },


    "TORRENT_CLIENTS" : {
        # Name your torrent clients here, for example, this example is named "Client1"
        "Client1" : {
            "torrent_client" : "qbit",
            "qbit_url" : "http://127.0.0.1",
            "qbit_port" : "8080",
            "qbit_user" : "username",
            "qbit_pass" : "password",

            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"
        },
        "qbit" : { #SAMPLE
            "torrent_client" : "qbit",
            "enable_search" : True,
            "qbit_url" : "http://127.0.0.1",
            "qbit_port" : "8080",
            "qbit_user" : "username",
            "qbit_pass" : "password",
            ### REPLACE $HOME with PATH: ie: /home/USER/ or on mac: USER/
            "torrent_storage_dir" : "$HOME/.local/share/qBittorrent/BT_backup", #: "$HOME/Library/Application Support/qBittorrent/BT_backup" , if windows: r"C:\APPDATA\qBittorrent\BT_backup" or LOCALAPPDATA 
            # if using DOCKER usually in  "/mnt/cache/appdata/qbittorrent/data/BT_backup/" HOWEVER input "/BT_backup" here
            # "qbit_tag" : "tag",
            # "qbit_cat" : "category",
            
            # Content Layout for adding .torrents: "Original"(recommended)/"Subfolder"/"NoSubfolder"
            "content_layout" : "Original",
            
            # Enable automatic torrent management if listed path(s) are present in the path
                # If using remote path mapping, use remote path
                # For using multiple paths, use a list ["path1", "path2"] 
            # "automatic_management_paths" : "",



            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "E:\\downloads\\tv",
            # "remote_path" : "/remote/downloads/tv",

            # Set to True to verify certificate for HTTPS connections; for instance, if the connection is using a self-signed certificate.
            "VERIFY_WEBUI_CERTIFICATE" : False,
        },

        "rtorrent" : { #SAMPLE
            "torrent_client" : "rtorrent",
            "rtorrent_url" : "https://user:password@server.host.tld:443/username/rutorrent/plugins/httprpc/action.php",
            # "torrent_storage_dir" : "path/to/session folder",
            # "rtorrent_label" : "Add this label to all uploads",

            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath",

        },
        "deluge" : { #SAMPLE
            "torrent_client" : "deluge",
            "deluge_url" : "localhost",
            "deluge_port" : "8080",
            "deluge_user" : "username",
            "deluge_pass" : "password",
            # "torrent_storage_dir" : "path/to/session folder",
            
            # Remote path mapping (docker/etc.) CASE SENSITIVE
            # "local_path" : "/LocalPath",
            # "remote_path" : "/RemotePath"
        },

        "transmission":  {
            'torrent_client': 'transmission',
            'transmission_url': 'http://localhost:9091', #change ip / port as needed
            'transmission_user': None,  # if authentication is needed 'user'
            'transmission_pass': None,  # if authentication is needed 'pass'
            'torrent_storage_dir': "/.config/transmission-daemon/Torrents/", #Linux use complete path, #Mac: "/Library/Application Support/Transmission/Torrents/"  #Windows: "C:\\Users\\$USER\\AppData\\Local\\transmission\\Torrents" change out $USER
            'enable_search': True  # if you want to implement search functionality
        },

        "watch" : { #SAMPLE
            "torrent_client" : "watch",
            "watch_folder" : "/Path/To/Watch/Folder",
        },

    },


    "DISCORD" :{
        "discord_bot_token" : "discord bot token",
        "discord_bot_description" : "Upload Assistant",
        "command_prefix" : "!",
        "discord_channel_id" : "discord channel id for use",
        "admin_id" : "your discord user id",

        "search_dir" : "Path/to/downloads/folder/   this is used for search",
        # Alternatively, search multiple folders:
        # "search_dir" : [
        #   "/downloads/dir1",
        #   "/data/dir2",
        # ]
        "discord_emojis" : {
                "BLU": "💙",
                "BHD": "🎉",
                "AITHER": "🛫",
                "STC": "📺",
                "ACM": "🍙",
                "MANUAL" : "📩",
                "UPLOAD" : "✅",
                "CANCEL" : "🚫"
        }
    }
}

