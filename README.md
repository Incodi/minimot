# minimot

I love data and I love Youtube, so this is a passion project.

run by cd'ing to the minimot directory and putting this command:
python src/app.py

This is a currently wonky program that can:
Count how many times a word or phrase appeared in a Youtuber's or Playlist's transcripts. (ana)
Count the first words or words of any position, to find the most common ones. (first_ana)
Visualize these counts.
Download transcripts en masse. (dloader) 

The downloader application downloads video subtitles and video metadata from a channel or playlist of choice.
It gets all metadata of the video, like view counts and duration
It is the most wonkiest part of this application as it uses yt-dlp and constantly freezes during downloading.
A way to circumvent the freezing is to close the entire program and run it again. 
The program will save and track the already downloaded data so the program does not need to download it again.

This data can be used in the analyzers. 

I want to improve on it after learning techniques in class. 
Maybe add an ML-like funcitonality where the program can predict what Youtuber a transcript is from after seeing two different bags of words and their counts from two different Youtubers.
Maybe add a sentiment analysis function.

For integrity, I did use AI pair programming for this project, especially for the programs with the ana suffix on it.
I learned from this that "vibe coding" truly does not work and one needs to understand the program to code with AI tools.
