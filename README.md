# **Home Express** *- self-developed telegram bot project*
**Home Express** is the telegram bot providing ETA information of Hong Kong public transportation with point-to-point matching and searching available route services for users. The transportation data is resourced from ***Data.Gov.HK***, and location data of users is collected and saved in the telegram server. None of user data will be stored and analyze in local device of developer. For Enquires, please contact [joechow.hok@gmail.com](joechow.hok@gmail.com).
___
# **To Developers / Hiring Manager**
The core operation file of telegram_bot is TG_Bot.py

The BackEnd supporting is Bus.py 
___
# *Operation*
1. How to start **Home Express**
1. Access Telegram Location
1. Search Available Route
1. Point-to-Point Match

## How to Use **Home Express** ?
### Access Telegram Location

Through the pin message and sending location features of telegram, Home Express allows users to send location data for setting target point or current point to perform services. To store the location data as target location, user may click the first button “儲存為目的地”.
> **EXAMPLE ?**
> 
> <img src="markdown_source/Save_Location.gif"/>

### Search Available Route

After sending location data to Home Express, user may choose searching feature to obtain the stops information nearby the location data.

> **EXAMPLE ?**
> 
> <img src="markdown_source/Search_Stops.gif"/>

### Point-to-Point Match

Given that the target location is saved as pinned message, user may send another location data for the point-to-point matching service.

>   **EXAMPLE ?**
>
>   <img src="markdown_source/Point-to-Point.gif"/>
