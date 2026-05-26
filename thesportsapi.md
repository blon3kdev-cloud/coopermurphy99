Getting Started:

 Introduction

Welcome to the documentation for iSports API.

Before using our api, please follow the steps below:

    Create an account.
    Start free trial or subscribe any plans to get access to the corresponding api endpoints.
    Log in to get your personal api key.

Each api endpoint has a unique path that replaces the <API_PATH> in the url below to call our data feed.

http://api.isportsapi.com/<API_PATH>?api_key=<YOUR_API_KEY>

For example, the path to Football Livescores for today is:

/sport/football/livescores

The complete request path is:

http://api.isportsapi.com/sport/football/livescores?api_key=<YOUR_API_KEY>

If http://api.isportsapi.com/ cannot be accessed, or the speed is slow, please use http://api2.isportsapi.com/. So here's another request path:

http://api2.isportsapi.com/sport/football/livescores?api_key=<YOUR_API_KEY>

Put your api key to replace <YOUR_API_KEY> in the request path, then you can get the corresponding result.


Football:

Common Api:

 League & Cup Profile (Basic)

Update Time: 2026-01-05 07:08
Introduction

This API endpoint returns the basic information of leagues and cups. If you need more details, please refer to League & Cup Profile. Click here to view 2000+ football leagues & cups.

Tips: You have access to all the football Common API endpoints with any valid paid football plans.
Related Plans

You can use this api by subscribing plans:  Stats,  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/league/basic
    Method: GET
    Calls: This interface is limited to 1800 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
leagueId	string	false	Get the league information of the specified leagueId.
Response

Parameter	Value	Description
leagueId 	string	
name 	string	Full name, e.g. Brazil Serie A
shortName 	string	Short name, e.g. BRA D1
type 	int	1: League
2: Cup
subLeagueName 	string	The on-going sub league of the league, e.g. Western Paly Off
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/league/basic?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/league/basic?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "leagueId": "111",
      "name": "Ireland Premier Division",
      "shortName": "IRE PR",
      "type": 1,
      "subLeagueName": "League"
    },
    {
      "leagueId": "122",
      "name": "Argentine Division 1",
      "shortName": "ARG D1",
      "type": 1,
      "subLeagueName": "League"
    }
  ]
}

 Schedule & Results (Basic)

Update Time: 2026-04-02 04:19Change Log
Introduction

This API endpoint returns the basic information of the match. If you need more details, please refer to Schedule & Results. You can use it with the Match Modify Record endpoint.

Tips: You have access to all the football Common API endpoints with any valid paid football plans.
Related Plans

You can use this api by subscribing plans:  Stats,  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/schedule/basic
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 12 hour/call
    Parameters: The request path needs at least one parameter (date, leagueId, and matchId ) to retrieve correct response. These three parameters can not be used at the same time. 

Parameter	Value	Required	Description
date	string	false	yyyy-MM-dd, e.g. 2019-08-01.
Return the match data of the specified date, the range is GMT+0 0:00-23:59; The historical schedule data is limited to query the past month.
leagueId	string	false	Returns the schedule result of the specified event; Returns the current season by default.
season	string	false	Use with leagueId to get the specified season, e.g. 2018-2019
Return to the current season by default.
matchId	string	false	Return the specified match data;
Multiple matches can be requested at the same time, and "matchId" is separated by ",", and a maximum of 100 matches can be queried at a time.
Response

Parameter	Value	Description
matchId 	string	
leagueId 	string	
leagueType 	int	1: League
2: Cup
leagueName 	string	Full name, e.g. Brazil Serie A
leagueShortName 	string	Short name, e.g. BRA D1
leagueColor 	string	
matchTime 	int	Match scheduled time, unix timestamp
status 	int	0: Not started
1: First half
2: Half-time break
3: Second half
4: Extra time
5: Penalty
-1: Finished
-10: Cancelled
-11: TBD
-12: Terminated
-13: Interrupted
-14: Postponed
homeId 	string	
homeName 	string	
awayId 	string	
awayName 	string	
homeScore 	int	
awayScore 	int	
homeHalfScore 	int	
awayHalfScore 	int	
explain 	string	Special case description of the match, e.g. Match end up with [0-3], due to (Torpedo-MAZ Minsk) withdraw from the match
extraExplain 	object	Return to Extra time, Penalty kicks, etc.
	kickOff 	int	1: Home kickoff
2: Away kickoff
minute 	int	How many minutes does the match have in regular time?
homeScore 	int	Regular time score, home team
awayScore 	int	Regular time score, away team
extraTimeStatus 	int	1: Normal matches extratime ends, "extraHomeScore/extraAwayScore" includes the regular time score
2: Special matches (e.g. beach football, indoor football) extratime ends, "extraHomeScore/extraAwayScore" does not include the regular time score
3: The match in extra time
extraHomeScore 	int	Extra time score, home team
extraAwayScore 	int	Extra time score, away team
penHomeScore 	int	Penalty score, home team
penAwayScore 	int	Penalty score, away team
twoRoundsHomeScore 	int	
twoRoundsAwayScore 	int	
winner 	int	Winner of the match
1: Home
2: Away
neutral 	boolean	Is it a neutral venue?
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/schedule/basic?api_key=<YOUR_API_KEY>&leagueId=1639";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/schedule/basic?api_key=<YOUR_API_KEY>&leagueId=1639

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "231035710",
      "leagueId": "122",
      "leagueType": 1,
      "leagueName": "Argentine Division 1",
      "leagueShortName": "ARG D1",
      "matchTime": 1564244100,
      "status": -1,
      "homeName": "Colon de Santa Fe",
      "awayName": "Patronato Parana",
      "homeScore": 0,
      "awayScore": 1,
      "explain": "",
      "extraExplain": {
        "kickOff": 0,
        "minute": 0,
        "homeScore": 0,
        "awayScore": 0,
        "extraTimeStatus": 0,
        "extraHomeScore": 0,
        "extraAwayScore": 0,
        "penHomeScore": 0,
        "penAwayScore": 0,
        "twoRoundsHomeScore": 0,
        "twoRoundsAwayScore": 0,
        "winner": 0
      },
      "neutral": false
    },
    {
      "matchId": "121035719",
      "leagueId": "122",
      "leagueType": 1,
      "leagueName": "Argentine Division 1",
      "leagueShortName": "ARG D1",
      "matchTime": 1564252200,
      "status": -1,
      "homeName": "San Lorenzo",
      "awayName": "Godoy Cruz Antonio Tomba",
      "homeScore": 3,
      "awayScore": 2,
      "explain": "",
      "extraExplain": {
        "kickOff": 0,
        "minute": 0,
        "homeScore": 0,
        "awayScore": 0,
        "extraTimeStatus": 0,
        "extraHomeScore": 0,
        "extraAwayScore": 0,
        "penHomeScore": 0,
        "penAwayScore": 0,
        "twoRoundsHomeScore": 0,
        "twoRoundsAwayScore": 0,
        "winner": 0
      },
      "neutral": false
    }
  ]
}

 Team Modify Record

Update Time: 2026-02-26 08:06Change Log
Introduction

This API endpoint returns the merge and deletion record of team id in the last 7 days.
Related Plans

You can use this api by subscribing plans:  Stats,  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/team/modify
    Method: GET
    Calls: This interface is limited to 60 minutes/call

Response

Parameter	Value	Description
data 	list	
	id 	int	
teamId 	int	
type 	string	merge or delete
toTeamId 	int	If delete, this field does not exist
modifyTime 	double	Modification time (unix timestamp)
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/team/modify?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/team/modify?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 3721,
      "teamId": 4572,
      "type": "merge",
      "toTeamId": 8746,
      "modifyTime": 1771469686
    },
    {
      "id": 3722,
      "teamId": 4572,
      "type": "delete",
      "modifyTime": 1771469710
    },
    {
      "id": 3725,
      "teamId": 25173,
      "type": "merge",
      "toTeamId": 2887,
      "modifyTime": 1771732360
    },
    {
      "id": 3726,
      "teamId": 3160,
      "type": "merge",
      "toTeamId": 4491,
      "modifyTime": 1771732529
    },
    {
      "id": 3727,
      "teamId": 3160,
      "type": "delete",
      "modifyTime": 1771732542
    },
    {
      "id": 3728,
      "teamId": 25173,
      "type": "delete",
      "modifyTime": 1771732560
    },
    {
      "id": 3729,
      "teamId": 3113,
      "type": "merge",
      "toTeamId": 5999,
      "modifyTime": 1771732725
    },
    {
      "id": 3730,
      "teamId": 3113,
      "type": "delete",
      "modifyTime": 1771732735
    },
    {
      "id": 3733,
      "teamId": 75610,
      "type": "merge",
      "toTeamId": 71541,
      "modifyTime": 1771744072
    },
    {
      "id": 3734,
      "teamId": 75610,
      "type": "delete",
      "modifyTime": 1771744099
    },
    {
      "id": 3744,
      "teamId": 60444,
      "type": "merge",
      "toTeamId": 45112,
      "modifyTime": 1771899763
    },
    {
      "id": 3745,
      "teamId": 60444,
      "type": "delete",
      "modifyTime": 1771899771
    },
    {
      "id": 3746,
      "teamId": 72680,
      "type": "merge",
      "toTeamId": 10874,
      "modifyTime": 1771900240
    },
    {
      "id": 3747,
      "teamId": 72680,
      "type": "delete",
      "modifyTime": 1771900270
    },
    {
      "id": 3748,
      "teamId": 73437,
      "type": "merge",
      "toTeamId": 66109,
      "modifyTime": 1771900436
    },
    {
      "id": 3749,
      "teamId": 73437,
      "type": "delete",
      "modifyTime": 1771900444
    },
    {
      "id": 3750,
      "teamId": 49377,
      "type": "merge",
      "toTeamId": 52625,
      "modifyTime": 1771900600
    },
    {
      "id": 3751,
      "teamId": 49377,
      "type": "delete",
      "modifyTime": 1771900613
    },
    {
      "id": 3758,
      "teamId": 78085,
      "type": "delete",
      "modifyTime": 1772012526
    }
  ]
}

 Player Modify Record

Update Time: 2026-02-26 08:06Change Log
Introduction

This API endpoint returns the merge and deletion record of player id in the last 7 days.
Related Plans

You can use this api by subscribing plans:  Stats,  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/player/modify
    Method: GET
    Calls: This interface is limited to 60 minutes/call

Response

Parameter	Value	Description
data 	list	
	id 	int	
playerId 	int	
type 	string	merge or delete
toPlayerId 	int	If delete, this field does not exist
modifyTime 	double	Modification time (unix timestamp)
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/player/modify?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/player/modify?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 3723,
      "playerId": 272768,
      "type": "merge",
      "toPlayerId": 349183,
      "modifyTime": 1771633242
    },
    {
      "id": 3724,
      "playerId": 272768,
      "type": "delete",
      "modifyTime": 1771633270
    },
    {
      "id": 3731,
      "playerId": 269869,
      "type": "merge",
      "toPlayerId": 296036,
      "modifyTime": 1771741552
    },
    {
      "id": 3732,
      "playerId": 269869,
      "type": "delete",
      "modifyTime": 1771741564
    },
    {
      "id": 3735,
      "playerId": 185313,
      "type": "merge",
      "toPlayerId": 182608,
      "modifyTime": 1771748818
    },
    {
      "id": 3736,
      "playerId": 262981,
      "type": "merge",
      "toPlayerId": 233407,
      "modifyTime": 1771749384
    },
    {
      "id": 3737,
      "playerId": 262981,
      "type": "delete",
      "modifyTime": 1771749460
    },
    {
      "id": 3738,
      "playerId": 355887,
      "type": "merge",
      "toPlayerId": 142992,
      "modifyTime": 1771831052
    },
    {
      "id": 3739,
      "playerId": 355887,
      "type": "delete",
      "modifyTime": 1771831132
    },
    {
      "id": 3740,
      "playerId": 355605,
      "type": "merge",
      "toPlayerId": 328291,
      "modifyTime": 1771831518
    },
    {
      "id": 3741,
      "playerId": 206503,
      "type": "merge",
      "toPlayerId": 223050,
      "modifyTime": 1771831677
    },
    {
      "id": 3742,
      "playerId": 206503,
      "type": "delete",
      "modifyTime": 1771832121
    },
    {
      "id": 3743,
      "playerId": 285645,
      "type": "merge",
      "toPlayerId": 301301,
      "modifyTime": 1771889163
    },
    {
      "id": 3752,
      "playerId": 363722,
      "type": "merge",
      "toPlayerId": 340436,
      "modifyTime": 1771909031
    },
    {
      "id": 3753,
      "playerId": 363722,
      "type": "delete",
      "modifyTime": 1771909515
    }
  ]
}

    Introduction
    Related Plans
    Request
    Response
    Example Request
    Example Response 

 Match Modify Record

Update Time: 2022-08-15 09:11
Introduction

This API endpoint returns the schedule deletion and match time modification record in the past 12 hours. You can use it with the Schedule & Results (Basic) endpoint.

Tips: You have access to all the football Common API endpoints with any valid paid football plans.
Related Plans

You can use this api by subscribing plans:  Stats,  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/schedule/modify
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 90 second/call

Response

Parameter	Value	Description
matchId 	string	
type 	string	modify or delete
matchTime 	int	Match time after modification.
Empty if the schedule is deleted.
Match scheduled time, unix timestamp
modifyTime 	int	When the match is modified, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/schedule/modify?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/schedule/modify?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "1729569",
      "type": "modify",
      "matchTime": 1561359600,
      "modifyTime": 1561360320
    },
    {
      "matchId": "1729555",
      "type": "modify",
      "matchTime": 1561406400,
      "modifyTime": 1561357920
    },
    {
      "matchId": "1729558",
      "type": "modify",
      "matchTime": 1561413600,
      "modifyTime": 1561357920
    }
  ]
}

 List of Countries

Update Time: 2022-05-30 03:59
Introduction

This API interface returns a list of all countries and the country ID.
Related Plans

You can use this api by subscribing plans:  Stats,  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/country
    Method: GET
    Calls: This interface is limited to 1800 second/call; 

Response

Parameter	Value	Description
countryId 	int	
country 	string	
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/country?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/country?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "countryId": 1,
      "country": "England"
    },
    {
      "countryId": 2,
      "country": "Italy"
    },
    {
      "countryId": 3,
      "country": "Spain"
    }
  ]
}

 Providers for European Markets

Update Time: 2026-01-29 02:30
Introduction

This API interface returns bookmaker IDs available for European market data.
Related Plans

You can use this api by subscribing plans:  Live Data,  Odds,  Odds Pro.
Request

    Path: /sport/football/bookmaker
    Method: GET
    Calls: This interface is limited to 1800 second/call; 

Response

Parameter	Value	Description
companyIdEu 	int	Bookmaker ID of [European Odds (200+ Bookmakers)] API.
companyName 	string	
companyIdMain 	int	Bookmaker ID of [Odds (18 bookmakers)] and [Other Odds] API.
If it returns "0", it means that [Odds (18 bookmakers)] and [Other Odds] API did not provide data for this bookmaker.
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/bookmaker?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/bookmaker?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "companyIdEu": 1,
      "companyName": "Vikingbet",
      "companyIdMain": 0
    },
    {
      "companyIdEu": 2,
      "companyName": "Betfair",
      "companyIdMain": 0
    },
    {
      "companyIdEu": 4,
      "companyName": "Nordicbet",
      "companyIdMain": 0
    }
  ]
}

 Schedule & Results

Update Time: 2022-05-30 04:16
Introduction

• This API is used to obtain the results of the live animation match schedule;

• The return schedule time range is the past 4 hours and the next 24 hours.
Related Plans

You can use this api by subscribing plans:  Live Animation.
Request

    Path: /sport/football/liveanimation/schedule
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 5 min/call

Response

Parameter	Value	Description
matchId 	string	
leagueType 	int	1: League
2: Cup
leagueId 	string	
leagueName 	string	Full name, e.g. Brazil Serie A
leagueShortName 	string	Short name, e.g. BRA D1
leagueColor 	string	
subLeagueId 	string	
subLeagueName 	string	The on-going sub league of the league, e.g. Western Paly Off
matchTime 	int	Match scheduled time, unix timestamp
halfStartTime 	int	The kick-off time of the first half or the second half, unix timestamp
status 	int	0: Not started
1: First half
2: Half-time break
3: Second half
4: Extra time
5: Penalty
-1: Finished
-10: Cancelled
-11: TBD
-12: Terminated
-13: Interrupted
-14: Postponed
homeId 	string	
homeName 	string	
awayId 	string	
awayName 	string	
homeScore 	int	Regular time score, home team
awayScore 	int	Regular time score, away team
homeHalfScore 	int	First half score, home team
awayHalfScore 	int	First half score, away team
homeRed 	int	
awayRed 	int	
homeYellow 	int	
awayYellow 	int	
homeCorner 	int	
awayCorner 	int	
homeRank 	string	The ranking of the team in the league, home team
awayRank 	string	The ranking of the team in the league, away team
season 	string	e.g. 2019-2020
round 	string	League round or cup stage, e.g. 10
group 	string	Cup group, e.g. A
location 	string	e.g. Camp Nou
weather 	string	e.g. Clear
temperature 	string	e.g. 14℃～15℃
explain 	string	Special case description of the match, e.g. Match end up with [0-3], due to (Torpedo-MAZ Minsk) withdraw from the match
extraExplain 	object	Return to Extra time, Penalty kicks, etc.
	kickOff 	int	1: Home kickoff
2: Away kickoff
minute 	int	How many minutes does the match have in regular time?
homeScore 	int	Regular time score, home team
awayScore 	int	Regular time score, away team
extraTimeStatus 	int	1: Normal matches extratime ends, "extraHomeScore/extraAwayScore" includes the regular time score
2: Special matches (e.g. beach football, indoor football) extratime ends, "extraHomeScore/extraAwayScore" does not include the regular time score
3: The match in extra time
extraHomeScore 	int	Extra time score, home team
extraAwayScore 	int	Extra time score, away team
penHomeScore 	int	Penalty score, home team
penAwayScore 	int	Penalty score, away team
twoRoundsHomeScore 	int	
twoRoundsAwayScore 	int	
winner 	int	Winner of the match
1: Home
2: Away
hasLineup 	boolean	Is there Lineup data?
neutral 	boolean	Is there Lineup data?
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/liveanimation/schedule?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/liveanimation/schedule?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "107018028",
      "leagueType": 1,
      "leagueId": "122",
      "leagueName": "Argentine Division 1",
      "leagueShortName": "ARG D1",
      "leagueColor": "#00CCCC",
      "subLeagueId": "123218",
      "subLeagueName": "League",
      "matchTime": 1637541000,
      "halfStartTime": 1637544896,
      "status": 3,
      "homeId": "5110",
      "homeName": "CA Platense",
      "awayId": "262",
      "awayName": "River Plate",
      "homeScore": 0,
      "awayScore": 1,
      "homeHalfScore": 0,
      "awayHalfScore": 1,
      "homeRed": 0,
      "awayRed": 0,
      "homeYellow": 0,
      "awayYellow": 3,
      "homeCorner": 5,
      "awayCorner": 5,
      "homeRank": "18",
      "awayRank": "1",
      "season": "2021-2022",
      "round": "21",
      "group": "",
      "location": "Vicentelopez Stadium",
      "weather": "Few Cloudy",
      "temperature": "26℃～27℃",
      "explain": "",
      "extraExplain": {
        "kickOff": 0,
        "minute": 0,
        "homeScore": 0,
        "awayScore": 0,
        "extraTimeStatus": 0,
        "extraHomeScore": 0,
        "extraAwayScore": 0,
        "penHomeScore": 0,
        "penAwayScore": 0,
        "twoRoundsHomeScore": 0,
        "twoRoundsAwayScore": 0,
        "winner": 0
      },
      "hasLineup": true,
      "neutral": false
    },
    {
      "matchId": "161145029",
      "leagueType": 1,
      "leagueId": "1033",
      "leagueName": "Turkish Super Liga",
      "leagueShortName": "TUR D1",
      "leagueColor": "#996600",
      "subLeagueId": "10965",
      "subLeagueName": "League",
      "matchTime": 1637600400,
      "halfStartTime": 0,
      "status": 0,
      "homeId": "530",
      "homeName": "Trabzonspor",
      "awayId": "1665",
      "awayName": "Gazisehir Gaziantep",
      "homeScore": 0,
      "awayScore": 0,
      "homeHalfScore": 0,
      "awayHalfScore": 0,
      "homeRed": 0,
      "awayRed": 0,
      "homeYellow": 0,
      "awayYellow": 0,
      "homeCorner": 0,
      "awayCorner": 0,
      "homeRank": "1",
      "awayRank": "12",
      "season": "2021-2022",
      "round": "13",
      "group": "",
      "location": "Huseyin Avni Aker Stadium",
      "weather": "Clear",
      "temperature": "10℃～11℃",
      "explain": "",
      "extraExplain": {
        "kickOff": 0,
        "minute": 0,
        "homeScore": 0,
        "awayScore": 0,
        "extraTimeStatus": 0,
        "extraHomeScore": 0,
        "extraAwayScore": 0,
        "penHomeScore": 0,
        "penAwayScore": 0,
        "twoRoundsHomeScore": 0,
        "twoRoundsAwayScore": 0,
        "winner": 0
      },
      "hasLineup": false,
      "neutral": false
    }
  ]
}

 Stats

Update Time: 2026-04-24 10:35Change Log
Introduction

This API endpoint returns instant technical statistics of football matches for the current day ( GMT +0 00:00-23:59 ).
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/stats
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 minute/call
    Parameters: 

Parameter	Value	Required	Description
date	string	false	yyyy-mm-dd, e.g. 2019-08-01, only for the matches in the past one month.
matchId	string	false	Search match with matchId.
Only supports querying matches from the current day.
Response

Parameter	Value	Description
matchId 	string	
stats 	list	
	type 	int	0: Kick-off
1: First corner
2: First yellow card
3: Shots
4: Shots on Goal
5: Fouls
6: Corner Kick
7: Corners (Overtime)
8: Free kick
9: Offside
10: Own goal
11: Yellow card
12: Yellow card (Overtime)
13: Red card
14: Possession%
15: Aerial
16: Save
17: Goalkeeper come out
18: Dispossessed
19: Successful Tackles
20: Interceptions
21: Long pass
22: Short pass
23: Assist
24: Successful center
25: First substitution
26: Last substitution
27: First offside
28: Last offside
29: Substitution
30: Last corner
31: Last yellow card
32: Substitution (Overtime)
33: Offside (Overtime)
34: Shots off goal
35: Hit The Post
36: Head Success
37: Blocked
38: Tackle
39: Dribbles
40: Throw-in
41: Passes
42: Pass Success%
43: Attacks
44: Dangerous attacks
45: Corner Kicks(HT)
46: Possession(HT)
47: BigChances
48: BigChancesMissed
49: ShotsInsideBox
50: ShotsOutsideBox
51: DuelsWon
52: ExpectedGoals （xG）
53: xGOpenPlay
54: xGSetPlay
55: xGNonPenalty
56: xGOT
57: Touches In Opposition Box
58: AccurateCrosses
59: GroundDuelsWon
60: AerialDuelsWon
61: Clearances
home 	string	Data of home team
away 	string	Data of away team
oprTime 	int	Update time. unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/stats?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/stats?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "391826613",
      "stats": [
        {
          "type": 6,
          "home": "0",
          "away": "8"
        },
        {
          "type": 45,
          "home": "0",
          "away": "5"
        },
        {
          "type": 11,
          "home": "2",
          "away": "0"
        },
        {
          "type": 3,
          "home": "11",
          "away": "16"
        },
        {
          "type": 4,
          "home": "8",
          "away": "5"
        },
        {
          "type": 34,
          "home": "3",
          "away": "11"
        },
        {
          "type": 43,
          "home": "107",
          "away": "100"
        },
        {
          "type": 44,
          "home": "56",
          "away": "87"
        }
      ]
    }
  ]
}

 League & Cup Profile

Update Time: 2026-01-05 07:10Change Log
Introduction

• This API endpoint returns the complete information of leagues and cups. Click here to view 2000+ football leagues & cups.

• Return to all events by default.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/league
    Method: GET
    Calls: This interface is limited to 1800 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
leagueId	string	false	Get the league information of the specified leagueId.
cmd	string，rule 	false	cmd=rule;
Get the description of the competition system. If there is no data, it will not be returned.
day	int	false	eg.day=50;
Returns league and cup data that have been modified within the specified number of days.
Response

Parameter	Value	Description
leagueId 	string	
type 	int	1: League
2: Cup
color 	string	RGB color code string, e.g. #9933FF
logo 	string	League logo url.

The picture is saved for local use, please do not call it directly.
name 	string	Full name, e.g. Brazil Serie A
shortName 	string	Short name, e.g. BRA D1
subLeagueName 	string	The on-going sub league of the league, e.g. Western Paly Off
totalRound 	int	
currentRound 	int	
currentSeason 	string	e.g. 2018-2019
countryId 	string	
country 	string	Country or region name, e.g. Brazil
countryLogo 	string	Country logo url.

The picture is saved for local use, please do not call it directly.
areaId 	int	0:International
1:Europe
2: America
3: Asia
4: Oceania
5: Africa
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/league?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/league?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "leagueId": "111",
      "type": 1,
      "color": "#9933FF",
      "logo": "http://zq.win007.com/Image/league_match/images/20181129190115.png",
      "name": "Ireland Premier Division",
      "shortName": "IRE PR",
      "subLeagueName": "League",
      "totalRound": 36,
      "currentRound": 23,
      "currentSeason": "2019",
      "countryId": "16",
      "country": "Ireland",
      "countryLogo": "http://zq.win007.com/Image/info/images/200712304261564347.gif",
      "areaId": 1
    },
    {
      "leagueId": "122",
      "type": 1,
      "color": "#00CCCC",
      "logo": "http://zq.win007.com/Image/league_match/images/20130917105542.jpg",
      "name": "Argentine Division 1",
      "shortName": "ARG D1",
      "subLeagueName": "League",
      "totalRound": 25,
      "currentRound": 6,
      "currentSeason": "2019-2020",
      "countryId": "38",
      "country": "Argentina",
      "countryLogo": "http://zq.win007.com/Image/info/images/20130121182844.jpg",
      "areaId": 2
    },
    {
      "leagueId": "133",
      "type": 1,
      "color": "#2f3fd2",
      "logo": "http://zq.win007.com/Image/league_match/images/20140122115024.jpg",
      "name": "Austrian Bundesliga",
      "shortName": "AUT D1",
      "subLeagueName": "League",
      "totalRound": 22,
      "currentRound": 7,
      "currentSeason": "2019-2020",
      "countryId": "14",
      "country": "Austria",
      "countryLogo": "http://zq.win007.com/Image/info/images/20130801165112.jpg",
      "areaId": 1
    },
    {
      "leagueId": "144",
      "type": 1,
      "color": "#996600",
      "logo": "http://zq.win007.com/Image/league_match/images/20170507175810.png",
      "name": "Brazil Serie A",
      "shortName": "BRA D1",
      "subLeagueName": "",
      "totalRound": 38,
      "currentRound": 18,
      "currentSeason": "2019",
      "countryId": "39",
      "country": "Brazil",
      "countryLogo": "http://zq.win007.com/Image/info/images/20130121200051.jpg",
      "areaId": 2
    },
    {
      "leagueId": "155",
      "type": 1,
      "color": "#FC9B0A",
      "logo": "http://zq.win007.com/Image/league_match/images/20181204180011.png",
      "name": "Belgian Pro League",
      "shortName": "BEL D1",
      "subLeagueName": "League",
      "totalRound": 30,
      "currentRound": 7,
      "currentSeason": "2019-2020",
      "countryId": "9",
      "country": "Belgium",
      "countryLogo": "http://zq.win007.com/Image/info/images/20130121180759.jpg",
      "areaId": 1
    }
  ]
}

 Cup Stage Profile

Update Time: 2022-05-30 04:02Change Log
Introduction

• This API endpoint is used to obtain the type data of the qualifying, knockout and other stages of the cup.

• Return to all cup stages by default.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/league/stage
    Method: GET
    Calls: This interface is limited to 1800 second/call;
    Recommend Calls: 1 day/call

Response

Parameter	Value	Description
leagueId 	string	
season 	string	e.g. 2018
stageId 	string	
stageName 	string	e.g. Qualifying Round
group 	boolean	Is it a group?
groupNum 	string	The number of groups.
currStage 	boolean	Is it currently in progress?
stageOrder 	string	The order of the different stages in the same cup.
lineCount 	string	The number of qualifying teams.
hasTwoLegs 	boolean	Whether this stage of the league is a two-round match?（One home and one away, two matches are decided to win or lose）
groupLineupCount 	int	The number of qualifying teams in each group.

This item may not be available, if there is, it will take precedence over lineCount.
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/league/stage?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/league/stage?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "leagueId": "156012",
      "season": "2018",
      "stageId": "15313",
      "stageName": "Qualifying Round",
      "group": false,
      "groupNum": "",
      "currStage": false,
      "stageOrder": "1",
      "lineCount": "",
      "hasTwoLegs": "true"
    },
    {
      "leagueId": "1572",
      "season": "2018",
      "stageId": "15770",
      "stageName": "Groups",
      "group": true,
      "groupNum": "8",
      "currStage": false,
      "stageOrder": "1",
      "lineCount": "0",
      "hasTwoLegs": "false"
    },
    {
      "leagueId": "1572",
      "season": "2018",
      "stageId": "15771",
      "stageName": "1/8 Final",
      "group": false,
      "groupNum": "",
      "currStage": false,
      "stageOrder": "2",
      "lineCount": "",
      "hasTwoLegs": "false"
    }
  ]
}

 Team Profile

Update Time: 2024-08-05 04:05Change Log
Introduction

• This API endpoint is used to obtain team information.

• Returns all teams by default.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/team
    Method: GET
    Calls: This interface is limited to 1800 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
leagueId	string	false	Get all the team information under the specified leagueId.

Not applicable for Cup IDs.
teamId	string	false	Get the team information of the specified teamId.
day	string	false	Return data that has been added or modified within this period, e.g. day=1or day=2
cmd=more	string	false	Get team introduction and team honors data.
Response

Parameter	Value	Description
teamId 	string	
leagueId 	string	
name 	string	
logo 	string	Team logo url.

The picture is saved locally for use, please do not call it directly.
foundingDate 	string	e.g. 1984 or 1890-9-6
address 	string	e.g. Avda. Aristides Maillol s/n，ES-08028 BARCELONA
area 	string	e.g. Barcelona
venue 	string	e.g. Camp Nou
capacity 	int	e.g. 99354
coach 	string	e.g. Txingurri Valverde
website 	string	Official website
isNational 	bool	Is it the national team?
country_logo 	string	Country logo (exists when it is a national team)
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/team?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/team?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "teamId": "15",
      "leagueId": "1514",
      "name": "SC Bregenz",
      "logo": "",
      "foundingDate": "1919",
      "address": "Sagerstrasse16900Bregenz",
      "area": "",
      "venue": "",
      "capacity": 0,
      "coach": "",
      "website": "http://www.swbregenz.at/"
    },
    {
      "teamId": "7",
      "leagueId": "1426",
      "name": "Grazer AK",
      "logo": "",
      "foundingDate": "1902-8-18",
      "address": "Stadionplatz 18041Graz",
      "area": "",
      "venue": "",
      "capacity": 0,
      "coach": "",
      "website": "http://www.gak.at/"
    },
    {
      "teamId": "8",
      "leagueId": "3",
      "name": "Austria Wien",
      "logo": "",
      "foundingDate": "1911",
      "address": "Fischhofgasse 14 1100 Wien",
      "area": "Wien",
      "venue": "Franz Horr Stadion",
      "capacity": 12200,
      "coach": "Thomas Letsch",
      "website": "http://www.fk-austria.at"
    }
  ]
}

 Team Profile for Search

Update Time: 2024-08-03 09:03
Introduction

This API endpoint supports searching team information by the team name.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/team/search
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Parameters: 

Parameter	Value	Required	Description
name	string	true	Get the data of the specified team name, supporting fuzzy search.
Response

Parameter	Value	Description
teamId 	string	
leagueId 	string	
name 	string	
logo 	string	Team logo url.
The picture is saved locally for use, please do not call it directly.
foundingDate 	string	e.g. 1984 or 1890-9-6
address 	string	e.g. Avda. Aristides Maillol s/n，ES-08028 BARCELONA
area 	string	e.g. Barcelona
venue 	string	e.g. Camp Nou
capacity 	int	e.g. 99354
coach 	string	e.g. Txingurri Valverde
website 	string	Official website
isNational 	bool	Is it the national team?
country_logo 	string	Country logo (exists when it is a national team)
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/team/search?api_key=<YOUR_API_KEY>&name=barcelona";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/team/search?api_key=<YOUR_API_KEY>&name=barcelona

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "teamId": "15",
      "leagueId": "1514",
      "name": "SC Bregenz",
      "logo": "",
      "foundingDate": "1919",
      "address": "Sagerstrasse16900Bregenz",
      "area": "",
      "venue": "",
      "capacity": 0,
      "coach": "",
      "website": "http://www.swbregenz.at/"
    },
    {
      "teamId": "7",
      "leagueId": "1426",
      "name": "Grazer AK",
      "logo": "",
      "foundingDate": "1902-8-18",
      "address": "Stadionplatz 18041Graz",
      "area": "",
      "venue": "",
      "capacity": 0,
      "coach": "",
      "website": "http://www.gak.at/"
    },
    {
      "teamId": "8",
      "leagueId": "3",
      "name": "Austria Wien",
      "logo": "",
      "foundingDate": "1911",
      "address": "Fischhofgasse 14 1100 Wien",
      "area": "Wien",
      "venue": "Franz Horr Stadion",
      "capacity": 12200,
      "coach": "Thomas Letsch",
      "website": "http://www.fk-austria.at"
    }
  ]
}

 Player Profile

Update Time: 2026-01-30 10:34Change Log
Introduction

• This API endpoint returns player information.

• At least one of the "teamId" "day"and "playerId" parameters must be filled in, and the three parameters can not be used at the same time.

• It is recommended to save all player data locally for the first time, and then update it regularly.

• The same player may be associated with 2 teams at the same time, including the national team and the club team. The uniqueness can be judged by "id".
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/player
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 1 day/call
    Parameters: Must add one of the two parameters teamId and playerId.

Parameter	Value	Required	Description
teamId	string	false	Get player data for a specified team.　teamId can`t be more than 50.
playerId	string	false	Get specified player data.
day	string	false	Get player data that has been modified within a specified number of days.
cmd=more	string	false	Get player honor data.
Response

Parameter	Value	Description
recordId 	string	
playerId 	string	
name 	string	
birthday 	string	e.g. 1987-02-02
height 	int	Unit: cm, e.g. 192
country 	string	e.g. Spain
feet 	string	Left or Right
weight 	int	Unit: kg, e.g. 77
photo 	string	Player photo url.

The picture is saved locally for use, please do not call it directly.
value 	long	Unit: 10,000 Euros, e.g. 2500
teamId 	string	
position 	string	e.g. Centre Back
number 	int	Player shirt number
introduce 	string	
contractEndDate 	string	When the contract ends, e.g. 2022-06-30
PAC 	string	Pace for players or Diving for goalkeepers.
SHO 	string	Shooting for players or Handling for goalkeepers.
PAS 	string	Passing for players or Kicking for goalkeepers.
DRI 	string	Dribbling for players or Reflexes for goalkeepers.
DEF 	string	Defending for players or Speed for goalkeepers.
PHY 	string	Physical for players or Positioning for goalkeepers.
country2 	string	Second nationality of the player, if available.
country2Id 	int	Unique identifier of the player’s second nationality.
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/player?api_key=<YOUR_API_KEY>&teamId=82";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/player?api_key=<YOUR_API_KEY>&teamId=82

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "recordId": "31891",
      "playerId": "2708",
      "name": "Nicolas Penneteau",
      "birthday": "1981-02-28",
      "height": 185,
      "country": "",
      "feet": "",
      "weight": 78,
      "photo": "http://zq.win007.com/Image/player/images/2014118140219.jpg",
      "value": 36,
      "teamId": "122",
      "position": "Goalkeeper",
      "number": 1,
      "introduce": "",
      "contractEndDate": "2020-06-30"
    }
  ]
}

 Player Profile for Search

Update Time: 2026-01-30 10:35
Introduction

This API endpoint supports searching player information by the player's name.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/player/search
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Parameters: 

Parameter	Value	Required	Description
name	string	true	Get the data of the specified player name, supporting fuzzy search.
Response

Parameter	Value	Description
recordId 	string	
playerId 	string	
name 	string	
birthday 	string	e.g. 1987-02-02
height 	int	Unit: cm, e.g. 192
country 	string	e.g. Spain
feet 	string	Left or Right
weight 	int	Unit: kg, e.g. 77
photo 	string	Player photo url
value 	long	Unit: ten thousand pounds, e.g. 3150
teamId 	string	
position 	string	e.g. Centre Back
number 	int	Player shirt number
introduce 	string	
contractEndDate 	string	When the contract ends, e.g. 2022-06-30
PAC 	string	Pace for players or Diving for goalkeepers.
SHO 	string	Shooting for players or Handling for goalkeepers.ability
PAS 	string	Passing for players or Kicking for goalkeepers.
DRI 	string	Dribbling for players or Reflexes for goalkeepers.
DEF 	string	Defending for players or Speed for goalkeepers.
PHY 	string	Physical for players or Positioning for goalkeepers.
country2 	string	Second nationality of the player, if available.
country2Id 	int	Unique identifier of the player’s second nationality.
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/player/search?api_key=<YOUR_API_KEY>&name=messi";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/player/search?api_key=<YOUR_API_KEY>&name=messi

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "recordId": "31891",
      "playerId": "2708",
      "name": "Nicolas Penneteau",
      "birthday": "1981-02-28",
      "height": 185,
      "country": "",
      "feet": "",
      "weight": 78,
      "photo": "http://zq.win007.com/Image/player/images/2014118140219.jpg",
      "value": 36,
      "teamId": "122",
      "position": "Goalkeeper",
      "number": 1,
      "introduce": "",
      "contractEndDate": "2020-06-30"
    }
  ]
}

 Teamlist with Player Profile

Update Time: 2022-06-23 10:30Change Log
Introduction

This API endpoint returns all team IDs with player profile.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/football/player
    Method: GET
    Calls: This interface is limited to 1800 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
cmd=teamlist	string	true	
Response

Parameter	Value	Description
teamId 	string	
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/player?api_key=<YOUR_API_KEY>&cmd=teamlist";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/player?api_key=<YOUR_API_KEY>&cmd=teamlist

{
  "code": 0,
  "message": "success",
  "data": [
    7,
    8,
    9,
    10,
    11
  ]
}

 Matches Analysis

Update Time: 2026-05-16 10:15Change Log
Introduction

• This API endpoint returns match analysis data for the past 24 hours and the next 7 days.

• The data includes Head to Head of the home team and away team, last match, future schedule, odds result statistics and goals statistics.

• Data cache 24 hours, do not need to update the data frequently, can be controlled.

• Data presentation：https://live5.nowgoal26.com/match/h2h-2591211
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/football/analysis
    Method: GET
    Calls: This interface is limited to 1 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	true	
Response

Parameter	Value	Description
headToHead 	list	Return up to the last 20 matches.
Each string contains all parameters below, separated by comma.
	matchId 	string	
league 	string	
leagueId 	string	
matchTime 	string	GMT+0, unix timestamp
home 	string	
homeTeamId 	string	
away 	string	
awayTeamId 	string	
scoreHome 	int	
scoreAway 	int	
homeHalfScore 	int	First half score, home team
awayHalfScore 	int	First half score, away team
homeRed 	int	
awayRed 	int	
homeCorner 	int	
awayCorner 	int	
initialHandicapHome 	string	Crown's handicap odds.
initialHandicap 	string	Crown's handicap odds.
initialHandicapAway 	string	Crown's handicap odds.
instantHandicapHome 	string	Crown's handicap odds.
instantHandicap 	string	Crown's handicap odds.
instantHandicapAway 	string	Crown's handicap odds.
initialHome 	string	Crown's european odds.
initialDraw 	string	Crown's european odds.
initialAway 	string	Crown's european odds.
instantHome 	string	Crown's european odds.
instantDraw 	string	Crown's european odds.
instantAway 	string	Crown's european odds.
initialOver 	string	Crown's over/under odds.
initialTotal 	string	Crown's over/under odds.
initialUnder 	string	Crown's over/under odds.
instantOver 	string	Crown's over/under odds.
instantTotal 	string	Crown's over/under odds.
instantUnder 	string	Crown's over/under odds.
homeLastMatches 	list	The same as HeadToHead.
Return up to the last 20 games.
Each string contains all parameters below, separated by comma.
awayLastMatches 	list	The same as HeadToHead.
Return up to the last 20 games.
Each string contains all parameters below, separated by comma.
homeSchedule 	list	Return to the next 5 schedule in the future.
Each string contains all parameters below, separated by comma.
	matchId 	string	
league 	string	
leagueId 	string	
matchTime 	string	e.g. 2019-03-30 21:00
home 	string	
homeTeamId 	string	
away 	string	
awayTeamId 	string	
day 	int	The gap days between the next game and the current game.
awaySchedule 	list	The same as HomeSchedule
Return to the next 5 schedule in the future.
Each string contains all parameters below, separated by comma.
homeOdds 	object	The odds result of the league.
	total 	object	Each string contains all parameters below, separated by comma.
	count 	int	
oddsWin 	int	It is a winning result when betting on the team, Crown's handicap odds.
oddsVoid 	int	It is a void result when betting on the team, Crown's handicap odds.
oddsLose 	int	It is a losing result when betting on the team, Crown's handicap odds.
oddsWinRate 	string	Rate of the winning result, Crown's handicap odds. e.g. 57.6%.
oddsOver 	int	The winning result is Over, Crown's over/under odds.
oddsOverRate 	string	Rate of the Over, Crown's over/under odds. e.g. 57.6%.
oddsUnder 	int	The winning result is Under, Crown's over/under odds
oddsUnderRate 	string	Rate of the Under, Crown's over/under odds. e.g. 57.6%.
home 	object	Data on home match.
The same as Total
Each string contains all parameters below, separated by comma.
away 	object	Data on away match.
The same as Total
Each string contains all parameters below, separated by comma.
recentSix 	object	Return up to the last 6 games' odds result.
Each string contains all parameters below, separated by comma.
	count 	int	
handicapResult 	string	w: Winning result
l: Losing result
v: Void result
e.g. lvlwlw
oddsWinRate 	string	Rate of the winning result, Crown's handicap odds. e.g. 57.6%.
overUnderResult 	string	o: Over result
u: Under result
v: Void result
e.g. ovouoo
totalHalf 	object	Data on the first half.
The same as Total
Each string contains all parameters below, separated by comma.
homeHalf 	object	Data on home match.
Data on the first half.
The same as Total
Each string contains all parameters below, separated by comma.
awayHalf 	object	Data on away match.
Data on the first half.
The same as Total
Each string contains all parameters below, separated by comma.
recentSixHalf 	object	Data on the first half.
The same as RecentSix
Each string contains all parameters below, separated by comma.
awayOdds 	object	The odds result of the league.
The same as HomeOdds
homeGoals 	object	The number of goals scored in the league.
Each string contains all parameters below, separated by comma.
	total 	object	
	0 	int	Number of matches without goals  
1 	int	Number of matches with one goal.
2 	int	Number of matches with two goals.
3 	int	Number of matches with three goals.
4+ 	int	Number of matches with more than four goals.
firstHalf 	int	Total number of goals in the first half.
secondHalf 	int	Total number of goals in the second half  
home 	object	Data on home match.
The same as Total
Each string contains all parameters below, separated by comma.
away 	object	Data on away match.
The same as Total
Each string contains all parameters below, separated by comma.
awayGoals 	object	The number of goals scored in the league.
The same as HomeGoals
homeHT 	object	First half and full score results.
	total 	object	Each string contains all parameters below, separated by comma.
	halfWinFullWin 	int	The number of matches that won in the first half and won in the match.
halfWinFullDraw 	int	The number of matches that won in the first half and drew in the match.
halfWinFullLose 	int	The number of matches that won in the first half and lost in the match.
halfDrawFullWin 	int	The number of matches that drew in the first half and won the match.
halfDrawFullDraw 	int	The number of matches that drew in the first half and drew the match.
halfDrawFullLose 	int	The number of matches that drew in the first half and lost the match.
halfLoseFullWin 	int	The number of matches that lost in the first half and won the match.
halfLoseFullDraw 	int	The number of matches that lost in the first half and drew the match.
halfLoseFullLose 	int	The number of matches that lost in the first half and lost the match.
home 	object	Data on home match.
The same as Total
Each string contains all parameters below, separated by comma.
away 	object	Data on away match.
The same as Total
Each string contains all parameters below, separated by comma.
awayHT 	object	First half and full score results.
The same as HomeHT
homeShootTime 	object	Number of goals at different times.
Each string contains all parameters below, separated by comma.
	Total 	object	Each string contains all parameters below, separated by comma.
	1-10 	int	Number of goals from 1 to 10 minutes.
11-20 	int	Number of goals from 11 to 20 minutes.
21-30 	int	Number of goals from 21 to 30 minutes.
31-40 	int	Number of goals from 31 to 40 minutes.
41-45+ 	int	Number of goals from 41 to 45+ minutes.
46-50 	int	Number of goals from 46 to 50 minutes.
51-60 	int	Number of goals from 51 to 60 minutes.
61-70 	int	Number of goals from 61 to 70 minutes.
71-80 	int	Number of goals from 71 to 80 minutes.
81-90+ 	int	Number of goals from 81 to 90+ minutes.
Home 	object	Data on home match.
The same as Total.
Each string contains all parameters below, separated by comma.
Away 	object	Data on away match.
The same as Total.
Each string contains all parameters below, separated by comma.
Time of ScoredTotal 	object	1st Shoot Time Statistics - total.
The same as Total.
Time of ScoredHome 	object	1st Shoot Time Statistics - home.
The same as Total.
Time of ScoredAway 	object	1st Shoot Time Statistics - away.
The same as Total.
awayShootTime 	object	Number of goals at different times
The same as HomeShootTime.
homeSingleDouble 	object	
	total 	object	Each string contains all parameters below, separated by comma.
	over 	int	
under 	int	
draw 	int	
odd 	int	
even 	int	
home 	object	Data on home match.
The same as Total
Each string contains all parameters below, separated by comma.
away 	object	Data on away match.
The same as Total.
Each string contains all parameters below, separated by comma.
awaySingleDouble 	object	The same as homeSingleDouble.
homeDataVs 	object	
	count 	int	Last 20 matches
scored 	int	Goals scored in the last 20 matches
conceded 	int	Goals conceded in the last 20 matches
win 	int	Number of wins in the last 20 matches
draw 	int	Draws in the last 20 matches
lose 	int	Number of losses in the last 20 matches
count 	int	Recent matches with the same home and away teams
scored 	int	Number of goals scored in the last 20 matches with the same home and away teams
conceded 	int	Number of goals conceded in the last 20 matches with the same home and away teams
win 	int	Recent wins of the home and away teams in the same matches
draw 	int	Recent draws between home and away teams in the same match
lose 	int	Recent losses of the home and away teams in the same matches
awayDataVs 	object	The same as homeDataVs..
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/analysis?api_key=<YOUR_API_KEY>&matchId=326192921";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/analysis?api_key=<YOUR_API_KEY>&matchId=326192921

{
  "code": 0,
  "message": "success",
  "data": {
    "headToHead": [
      "260604714,SPA D1,1134,1571502600,Getafe,98,Leganes,992,2,0,0,0,0,0,2,3,0.95, 0.5, 0.93, 0.92, 0.25, 0.99,1.94, 3.05, 4.25, 2.28, 2.85, 4.00,0.80, 1.75, 1.06, 0.96, 1.75, 0.94",
      "377438515,SPA D1,1134,1553947200,Getafe,98,Leganes,992,0,2,0,0,0,0,3,4,1.06, 0.75, 0.82, 0.96, 0.5, 0.95,1.77, 3.20, 5.00, 1.96, 3.10, 4.90,0.96, 2, 0.90, 0.95, 1.75, 0.95",
      "2586919,SPA D2,1336,1085324400,Leganes,992,Getafe,98,0,0,0,0,0,0,,,, , , , , ,, , , , , ,, , , , , "
    ],
    "homeLastMatches": [
      "110152818,SPA CUP,1189,1578754800,Real Murcia,117,Leganes,992,0,4,0,1,0,0,0,5,0.80, -0.75, 1.02, 0.80, -0.75, 1.02,3.85, 3.35, 1.78, 4.15, 3.25, 1.76,0.79, 2.25, 1.01, 1.02, 2.25, 0.78",
      "201704710,SPA D1,1134,1578074400,Real Valladolid,123,Leganes,992,2,2,1,2,0,0,4,3,1.05, 0.25, 0.83, 0.92, 0, 0.98,2.36, 3.00, 3.10, 2.88, 2.81, 2.95,1.05, 2, 0.81, 0.97, 1.75, 0.93"
    ],
    "awayLastMatches": [
      "120152819,SPA CUP,1189,1578765600,CF Badalona,975,Getafe,98,2,0,0,0,0,1,1,3,0.85, -2, 0.97, 0.75, -1.5, 1.07,11.50, 6.10, 1.15, 7.00, 4.65, 1.31,0.91, 3, 0.89, 0.90, 2.75, 0.90",
      "250704714,SPA D1,1134,1578150000,Getafe,98,Real Madrid,82,0,3,0,1,0,0,7,4,0.83, -0.75, 1.05, 0.95, -0.5, 0.95,3.90, 3.65, 1.82, 4.30, 3.40, 1.95,1.03, 2.75, 0.83, 0.94, 2.25, 0.96"
    ],
    "homeSchedule": [
      "111303817,SPA CUP,1189,1579802400,CD Ebro,21398,Leganes,992,6",
      "222704713,SPA D1,1134,1580036400,Atletico Madrid,109,Leganes,992,9"
    ],
    "awaySchedule": [
      "252704716,SPA D1,1134,1580050800,Getafe,98,Real Betis,96,9",
      "213704713,SPA D1,1134,1580655600,Athletic Bilbao,92,Getafe,98,16"
    ]
  }
}

 List of Player Stats (Match)

Update Time: 2026-04-02 04:26Change Log
Introduction

• This API endpoint returns match list which contains players' technical statistics within one day (24H). You can use it with the Player Stats (Match) endpoint.

• Currently only some top leagues are supported.

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/football/playerstats/match/list
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 12 hour/call

Response

Parameter	Value	Description
matchId 	string	
matchTime 	int	Match scheduled time, unix timestamp
leagueName 	string	
homeName 	string	
awayName 	string	
modifyTime 	int	
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/playerstats/match/list?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/playerstats/match/list?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "303967612",
      "matchTime": 1567951200,
      "leagueName": "Brazil Serie A",
      "homeName": "Cruzeiro (MG)",
      "awayName": "Gremio (RS)"
    },
    {
      "matchId": "343967616",
      "matchTime": 1567980000,
      "leagueName": "Brazil Serie A",
      "homeName": "Centro Sportivo Alagoano",
      "awayName": "Chapecoense SC"
    },
    {
      "matchId": "363967618",
      "matchTime": 1567969200,
      "leagueName": "Brazil Serie A",
      "homeName": "Botafogo RJ",
      "awayName": "Atletico Mineiro"
    },
    {
      "matchId": "493967611",
      "matchTime": 1567969200,
      "leagueName": "Brazil Serie A",
      "homeName": "Santos",
      "awayName": "Atletico Paranaense"
    },
    {
      "matchId": "211644714",
      "matchTime": 1567951200,
      "leagueName": "Portugal Primera Liga",
      "homeName": "Rio Ave",
      "awayName": "Vitoria Guimaraes"
    }
  ]
}

 Player Stats (Match)

Update Time: 2026-05-16 10:17Change Log
Introduction

• This API endpoint returns players' technical statistics of specified matchId. You can use it with the List of Player Stats (Match) endpoint.

• Currently only some top leagues are supported.

• support to check back the matches within a week.
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/football/playerstats/match
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 minute/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	true	for detailed statistical data specified match;
support to check back the matches within a week.
Response

Parameter	Value	Description
playerId 	string	
teamId 	string	
number 	int	
name 	string	
positionName 	string	
shots 	int	
shotsTarget 	int	
keyPass 	int	
passRate 	string	
aerialWon 	int	
touches 	int	
dribblesWon 	int	
wasFouled 	int	
dispossessed 	int	
turnOver 	int	
offsides 	int	
tackles 	int	
interception 	int	
clearances 	int	
clearanceWon 	int	
shotsBlocked 	int	
offsideProvoked 	int	
fouls 	int	
totalPass 	int	
accuratePass 	int	
crossNum 	int	
crossWon 	int	
longBall 	int	
longBallWon 	int	
throughBall 	int	
throughBallWon 	int	
rating 	string	
red 	int	
yellow 	int	
assist 	int	
playingTime 	int	
goals 	int	
firstTeam 	boolean	Is the player in the starting lineup?
penaltyGoals 	int	
shotOnPost 	int	
errorLeadToGoal 	int	
secondYellow 	int	
penaltySave 	int	
isBest 	boolean	Is it the best player?
duelTotal 	int	Total 1v1 duels a player participated in.
aerialTotal 	int	Aerial duels won by the player.
highClaims 	int	High balls successfully claimed (mainly by goalkeeper).
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/playerstats/match?api_key=<YOUR_API_KEY>&matchId=489644922";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/playerstats/match?api_key=<YOUR_API_KEY>&matchId=489644922

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "playerId": "113213",
      "teamId": "778",
      "number": 1,
      "name": "Alisson Becker",
      "positionName": "Goalkeeper",
      "shots": 0,
      "shotsTarget": 0,
      "keyPass": 0,
      "passRate": "0.9",
      "aerialWon": 0,
      "touches": 27,
      "dribblesWon": 0,
      "wasFouled": 0,
      "dispossessed": 0,
      "turnOver": 0,
      "offsides": 0,
      "tackles": 0,
      "interception": 0,
      "clearances": 0,
      "clearanceWon": 0,
      "shotsBlocked": 0,
      "offsideProvoked": 0,
      "fouls": 0,
      "totalPass": 20,
      "accuratePass": 18,
      "crossNum": 0,
      "crossWon": 0,
      "longBall": 2,
      "longBallWon": 0,
      "throughBall": 0,
      "throughBallWon": 0,
      "rating": "6.97",
      "red": 0,
      "yellow": 0,
      "assist": 0,
      "playingTime": 80,
      "goals": 0,
      "firstTeam": true,
      "penaltyGoals": 0,
      "shotOnPost": 0,
      "errorLeadToGoal": 0,
      "secondYellow": 0,
      "penaltySave": "0",
      "isBest": false
    }
  ]
}

 List of Player Stats (League & Cup)

Update Time: 2026-04-02 05:29
Introduction

• This API endpoint returns league list which contains players' seasonal technical statistics. You can use it with Player Stats (League&Cup) endpoint.

• By using endpoint League & Cup Profile (Basic) , you can get basic information of leagues and cups.
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/football/playerstats/league/list
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 1 day/call

Response

Parameter	Value	Description
leagueId 	string	
season 	string	e.g. 2018-2019
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/playerstats/league/list?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/playerstats/league/list?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "leagueId": "122",
      "season": "2019-2020"
    },
    {
      "leagueId": "144",
      "season": "2019"
    },
    {
      "leagueId": "188",
      "season": "2019-2020"
    },
    {
      "leagueId": "199",
      "season": "2019-2020"
    },
    {
      "leagueId": "1011",
      "season": "2019-2020"
    },
    {
      "leagueId": "1112",
      "season": "2019-2020"
    },
    {
      "leagueId": "1617",
      "season": "2019-2020"
    },
    {
      "leagueId": "1123",
      "season": "2019"
    },
    {
      "leagueId": "1325",
      "season": "2019-2020"
    },
    {
      "leagueId": "1527",
      "season": "2019"
    },
    {
      "leagueId": "1033",
      "season": "2019-2020"
    },
    {
      "leagueId": "1134",
      "season": "2019-2020"
    },
    {
      "leagueId": "1437",
      "season": "2019-2020"
    },
    {
      "leagueId": "1639",
      "season": "2019-2020"
    },
    {
      "leagueId": "1730",
      "season": "2019-2020"
    },
    {
      "leagueId": "1066",
      "season": "2019"
    },
    {
      "leagueId": "1572",
      "season": "2018"
    }
  ]
}

 Player Stats (League & Cup)

Update Time: 2026-04-02 04:29Change Log
Introduction

• This API endpoint returns players' seasonal technical statistics of specified league or cup id. You can use it with List of Player Stats (League&Cup) endpoint.

• The data return distinguishes between home and away matches, and the total data needs to be aggregated through home and away matches.
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/football/playerstats/league
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
leagueId	string	true	get the statistics of the specified league and cup.
Response

Parameter	Value	Description
playerId 	string	
teamId 	string	
leagueId 	string	
season 	string	e.g. 2018-2019
appearanceCount 	int	Total appearences in the season
substituteCount 	int	
playingTime 	int	Minutes played in the season
goals 	int	Penalty not included
penaltyGoals 	int	
shotCount 	int	
shotTargetCount 	int	
wasFouledCount 	int	
offsideCount 	int	
bestCount 	int	
rating 	string	Average player rating in all games.
passCount 	int	
passSuccessCount 	int	
keyPassCount 	int	
assistCount 	int	
longPassCount 	int	
longPassSuccessCount 	int	
throughPassCount 	int	
throughPassSuccessCount 	int	
dribblesSuccessCount 	int	
crossPassCount 	int	
crossPassSuccessCount 	int	
tackleCount 	int	
interceptionCount 	int	
clearanceCount 	int	
dispossessedCount 	int	
shotBlockedCount 	int	
aerialSuccessCount 	int	
foulsCount 	int	
redCount 	int	
yellowCount 	int	
turnOverCount 	int	
modifyTime 	int	Modify time, unix timestamp
homeTeam 	boolean	Is it home team player stats?
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/playerstats/league?api_key=<YOUR_API_KEY>&leagueId=1617";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/playerstats/league?api_key=<YOUR_API_KEY>&leagueId=1617

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "playerId": "82773",
      "teamId": "265",
      "leagueId": "122",
      "season": "2019-2020",
      "appearanceCount": 1,
      "substituteCount": 0,
      "playingTime": 75,
      "goals": 1,
      "penaltyGoals": 0,
      "shotCount": 1,
      "shotTargetCount": 1,
      "offsideCount": 1,
      "bestCount": 1,
      "rating": "7.93",
      "passCount": 29,
      "passSuccessCount": 22,
      "keyPassCount": 1,
      "assistCount": 0,
      "longPassCount": 0,
      "longPassSuccessCount": 0,
      "throughPassCount": 0,
      "throughPassSuccessCount": 0,
      "dribblesSuccessCount": 1,
      "crossPassCount": 2,
      "crossPassSuccessCount": 1,
      "tackleCount": 2,
      "interceptionCount": 1,
      "clearanceCount": 1,
      "dispossessedCount": 0,
      "shotBlockedCount": 0,
      "aerialSuccessCount": 2,
      "foulsCount": 2,
      "redCount": 0,
      "yellowCount": 0,
      "turnOverCount": 0,
      "modifyTime": 1567283939,
      "homeTeam": false
    }
  ]
}

 Top Scorer

Update Time: 2026-04-02 05:30Change Log
Introduction

• This interface is used to obtain the technical statistics of players' goals in league and cup matches, which can be used as a reference to make the scorer list.

• Currently only some major leagues and cups are supported.

• By using endpoint League & Cup Profile (Basic) , you can get basic information of leagues and cups.
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/football/topscorer
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 day/call
    Parameters: 

Parameter	Value	Required	Description
leagueId	string	true	get the current season data of the specified league and cup.
season	string	false	to get the specified season data of the event, it needs to be used together with "leagueId".

e.g. 2019 or 2018-2019
Response

Parameter	Value	Description
playerId 	string	
playerName 	string	
teamId 	string	
teamName 	string	
country 	string	
goalsCount 	int	Total goals, including penalty
homeGoals 	int	Goals in home matches, including penalty
awayGoals 	int	Goals in away matches, including penalty
homePenalty 	int	Penalty in home matches.
awayPenalty 	int	Penalty in away matches.
matchNum 	int	Number of appearances.

Some cup matches do not have this field.
subNum 	int	Number of substitute appearances.

Some cups do not have this field.
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/topscorer?api_key=<YOUR_API_KEY>&leagueId=122";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/topscorer?api_key=<YOUR_API_KEY>&leagueId=122

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "playerId": "66150",
      "playerName": "Matias Suarez",
      "teamId": "",
      "teamName": "River Plate",
      "country": "",
      "goalsCount": 3,
      "homeGoals": 2,
      "awayGoals": 1,
      "homePenalty": 0,
      "awayPenalty": 0
    },
    {
      "playerId": "128038",
      "playerName": "Rafael Santos Borre Maury",
      "teamId": "",
      "teamName": "River Plate",
      "country": "",
      "goalsCount": 3,
      "homeGoals": 1,
      "awayGoals": 2,
      "homePenalty": 1,
      "awayPenalty": 0
    }
  ]
}

 Pre-match and In-play Odds (Main)

Update Time: 2026-04-02 04:05
Introduction

• This API endpoint returns main market odds, including: handicap、europeOdds、overUnder 、handicapHalf and overUnderHalf.

• You can get the unplayed and in-play matches with odds in the next 14 days, including pre-match and In-play Odds (Main).You can use it with the Live Odds Changes (Main) endpoint.

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.

• Handicap and overUnder description:
-Handicap is an integer multiple of 0.25, 0 means "0 goal", 0.25 means "0/0.5 goal", 0.5 means "0.5 goal", 0.75 means "0.5/1 goal", 1 means "1 goal" , And so on;

• A positive number means the home team's handicap, a negative number means the away team's handicap.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 7: SNAI, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwetten, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin, 50:1xbet

• “Whether Closed”only supports some companies:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/main
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 minute/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed, and the prefix "instant" means the live one that will be changed.

Parameter	Value	Description
handicap 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is there inplay odds?
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
europeOdds 	string array	Known as 1x2 odds. Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnder 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
handicapHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnderHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/main?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/main?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "381964615,1,0.5,1.08,0.72,0.5,1.05,0.75,false,false,1570502888,false",
      "381964615,3,0.25,0.97,0.85,0.25,0.78,1.11,false,true,1570690813,false",
      "381964615,8,0.25,1.00,0.85,0.5,1.10,0.78,false,false,1570674646,false",
      "381964615,12,0.25,0.95,0.95,0.5,1.08,0.83,false,false,1570692013,false"
    ],
    "europeOdds": [
      "381964615,22,2.25,3.10,3.10,2.05,3.35,3.55,1570657560,false",
      "381964615,24,2.20,3.10,2.95,2.12,3.20,3.40,1570591080,false",
      "381964615,1,2.05,3.20,3.30,2.05,3.25,3.25,1570591440,false",
      "381964615,14,2.30,3.20,3.20,2.05,3.25,3.75,1570692060,false",
      "381964615,4,2.30,3.10,3.20,2.05,3.20,3.75,1570692300,false"
    ],
    "overUnder": [
      "381964615,1,2.25,0.94,0.76,2.25,0.94,0.76,1570459441,false",
      "381964615,3,2.25,0.99,0.81,2.25,1.02,0.84,1570690813,false",
      "381964615,4,2.5,1.25,0.57,2.5,1.25,0.57,1569496411,false",
      "381964615,8,2.25,1.02,0.82,2.25,1.02,0.82,1570523846,false",
      "381964615,12,2.25,1.15,0.78,2.25,1.02,0.87,1570690912,false"
    ],
    "handicapHalf": [
      "381964615,1,0.25,1.10,0.65,0.25,1.10,0.65,1570459441",
      "381964615,3,0,0.70,1.13,0.25,1.23,0.69,1570690814",
      "381964615,8,0,0.70,1.10,0.25,1.20,0.65,1570458025",
      "381964615,12,0,0.70,1.26,0.25,1.25,0.65,1570691460",
      "381964615,17,0,0.69,1.18,0.25,1.33,0.63,1570589056",
      "381964615,22,0,0.62,1.21,0.25,1.26,0.65,1570682079"
    ],
    "overUnderHalf": [
      "381964615,1,0.75,0.66,1.04,0.75,0.66,1.04,1570459442",
      "381964615,3,0.75,0.71,1.09,0.75,0.73,1.14,1570690814",
      "381964615,8,0.75,0.72,1.08,0.75,0.72,1.08,1570674802",
      "381964615,12,0.75,0.86,1.03,0.75,0.69,1.18,1570691460",
      "381964615,17,0.75,0.76,1.06,0.75,0.77,1.12,1570589056"
    ]
  }
}

 Live Odds Changes (Main)

Update Time: 2026-04-02 05:15
Introduction

This API endpoint returns odds that changed in past 20 seconds. You can use it with the Pre-match and In-play Odds (Main) endpoint.
Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/main/changes
    Method: GET
    Calls: This interface is limited to 1 second/call;
    Recommend Calls: 2 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
handicap 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is there inplay odds?
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
europeOdds 	string array	Known as 1x2 odds. Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHome 	string	
instantDraw 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnder 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
handicapHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnderHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/main/changes?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/main/changes?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "391964616,23,-1.25,0.75,1.17,false,false,1570693111,false",
      "348074610,23,1.25,1.12,0.79,false,false,1570693112,false",
      "241174614,3,0.25,0.96,0.94,false,true,1570693105,false",
      "241174614,24,0.25,0.97,0.95,false,false,1570693096,false"
    ],
    "europeOdds": [
      "241174614,23,2.25,3.30,3.30,1570693140,false",
      "495968614,42,2.10,3.45,3.35,1570693140,false",
      "211715713,47,1.07,11.08,31.93,1570693140,false"
    ],
    "overUnder": [
      "391964616,23,2.5,0.79,1.09,1570693111,false",
      "255352718,42,3,0.94,0.79,1570693103,false",
      "379724717,23,2,1.01,0.89,1570693115,false",
      "319615710,14,5.5,0.83,0.95,1570693105,false",
      "319615710,22,5.75,0.93,0.85,1570693098,false"
    ],
    "handicapHalf": [
      "255352718,42,-0.25,1.02,0.76,1570693103",
      "207615717,24,1.25,0.95,0.89,1570693096",
      "319615710,22,2.5,0.90,0.88,1570693098",
      "211715713,47,1,0.75,1.07,1570693112",
      "319715711,24,0.25,0.89,0.95,1570693096",
      "222266716,31,-0.25,1.03,0.81,1570693115"
    ],
    "overUnderHalf": [
      "391964616,8,1,0.72,1.08,1570693115",
      "319615710,22,2.5,0.76,1.00,1570693098",
      "211715713,47,1.5,1.05,0.76,1570693112",
      "222540812,22,1.25,0.90,0.84,1570693098"
    ]
  }
}

 Historical Odds (Main)

Update Time: 2026-05-16 10:15Change Log
Introduction

• This API endpoint returns the historical initial and final odds data of the main market of the match.

• By default, it returns the match data from GMT+0 0:00 to the currently completed match.

• Data includes: handicap、handicapHalf、europeOdds、overUnder and overUnderHalf.

• Handicap and overUnder description:
-Handicap is an integer multiple of 0.25, 0 means "0 goal", 0.25 means "0/0.5 goal", 0.5 means "0.5 goal", 0.75 means "0.5/1 goal", 1 means "1 goal" , And so on;

• A positive number means the home team's handicap, a negative number means the away team's handicap.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 7: SNAI, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwette, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin, 50:1xbet

• “Whether Closed”only supports some companies:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/main/history
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 10 minute/call
    Parameters: 

Parameter	Value	Required	Description
date	string	false	Get the match data of the specified date, the range is from GMT +0 0:00-23:59;
Support one month of back-checking.

yyyy-MM-dd, e.g. date=2019-08-01.
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId.

e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId.

e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed. As for historical odds, the prefix "instant" means the last one before the match.

Parameter	Value	Description
handicap 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is it inplay odds?
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
europeOdds 	string array 	Known as 1x2 odds. Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
overUnder 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
handicapHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
overUnderHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/main/history?api_key=<YOUR_API_KEY>&matchId=326192921";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/main/history?api_key=<YOUR_API_KEY>&matchId=326192921

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "100582128,8,0.25,0.93,0.88,0.25,1.00,0.80,false,true,1638402666,true",
      "100582128,12,0.25,1.02,0.77,0.25,1.02,0.77,false,true,1638402715,true",
      "100582128,17,0.25,0.82,0.83,0.25,0.82,0.83,false,true,1638402325,true"
    ],
    "europeOdds": [
      "100582128,8,2.15,3.30,2.88,2.20,3.30,2.80,1638402735,true",
      "100582128,12,2.20,3.30,2.60,2.20,3.30,2.60,1638402715,true"
    ],
    "overUnder": [
      "100582128,8,2.5,0.95,0.85,2.5,0.95,0.85,1638402666,true",
      "100582128,12,2.5,0.90,0.87,2.5,0.90,0.87,1638402715,true"
    ],
    "handicapHalf": [
      "100582128,8,0,0.70,1.10,0,0.75,1.05,1638397531",
      "100582128,12,0,0.77,1.02,0,0.89,0.91,1638398737"
    ],
    "overUnderHalf": [
      "100582128,8,1,0.95,0.85,1,0.95,0.85,1638397531",
      "100582128,12,1,0.90,0.87,0.5,3.20,0.15,1638398737"
    ]
  }
}|

 Future Odds (Main)

Update Time: 2026-01-24 01:53
Introduction

• This API endpoint returns main instant odds of all games after 10 days.

• Data includes: handicap、handicapHalf、europeOdds、overUnder and overUnderHalf.

• Handicap and overUnder description:
-Handicap is an integer multiple of 0.25, 0 means "0 goal", 0.25 means "0/0.5 goal", 0.5 means "0.5 goal", 0.75 means "0.5/1 goal", 1 means "1 goal" , And so on;

• A positive number means the home team's handicap, a negative number means the away team's handicap.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 7: SNAI, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwette, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin, 50:1xbet

• “Whether Closed”only supports some companies:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/main/future
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 10 minute/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed, and the prefix "instant" means the live one that will be changed.

Parameter	Value	Description
handicap 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is it inplay odds?
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
europeOdds 	string array 	Known as 1x2 odds. Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
overUnder 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
handicapHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
changeTime 	int	Change time, unix timestamp
overUnderHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
changeTime 	int	Change time, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/main/future?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/main/future?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "495964610,24,0.75,0.67,1.33,false,false,3,1570693403,false",
      "499964614,3,1.25,0.96,0.94,false,true,1,1570693410,false"
    ],
    "europeOdds": [
      "210824713,19,1.83,3.25,4.85,1,1570693440,false",
      "210824713,7,1.75,3.25,4.75,1,1570693440,false",
      "284350819,12,1.7,3.50,4.50,1,1570693440,false"
    ],
    "overUnder": [
      "485968613,22,2.75,1.04,0.83,1,1570693406,false",
      "485968613,22,2.5,0.78,1.09,2,1570693406,false",
      "485968613,31,2.75,1.04,0.86,1,1570693400,false"
    ],
    "handicapHalf": [
      "245074617,24,-0.75,1.33,0.63,false,2,1570693403",
      "485968613,22,0.5,0.94,0.88,false,1,1570693406",
      "485968613,31,0.5,0.95,0.93,false,1,1570693400"
    ],
    "overUnderHalf": [
      "485968613,3,1,0.78,1.02,1,1570693398",
      "485968613,3,1.25,1.20,0.63,2,1570693410"
    ]
  }
}

 Pre-match and In-play Odds (All)

Update Time: 2026-04-02 05:16
Introduction

• This API endpoint returns multi market odds, including: handicap、europeOdds、overUnder、handicapHalf and overUnderHalf.

• The content of the API is consistent with the API [Pre-match and In-play Odds (Main)], and the data of " handicapIndex" = 1 is the data of the main market.

• You can get the unplayed and in-play matches with odds in the next 14 days, including pre-match and In-play Odds(All).You can use it with the Live Odds Changes (All) endpoint.

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.

• Handicap and overUnder description:
-Handicap is an integer multiple of 0.25, 0 means "0 goal", 0.25 means "0/0.5 goal", 0.5 means "0.5 goal", 0.75 means "0.5/1 goal", 1 means "1 goal" , And so on;

• A positive number means the home team's handicap, a negative number means the away team's handicap.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 7: SNAI, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwette, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin, 50:1xbet

• “Whether Closed”only supports some companies:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/all
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 minute/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed, and the prefix "instant" means the live one that will be changed.

Parameter	Value	Description
handicap 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is there inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
handicapCount 	int	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
europeOdds 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
handicapIndex 	int	There is no multi-odds for europeOdds, and the handicapIndex is all 1.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnder 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
handicapHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
inPlay 	boolean	Is there inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnderHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/all?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/all?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "391964616,23,-1.25,0.75,1.17,false,false,1570693111,false",
      "348074610,23,1.25,1.12,0.79,false,false,1570693112,false",
      "241174614,3,0.25,0.96,0.94,false,true,1570693105,false",
      "241174614,24,0.25,0.97,0.95,false,false,1570693096,false"
    ],
    "europeOdds": [
      "241174614,23,2.25,3.30,3.30,1570693140,false",
      "495968614,42,2.10,3.45,3.35,1570693140,false",
      "211715713,47,1.07,11.08,31.93,1570693140,false"
    ],
    "overUnder": [
      "391964616,23,2.5,0.79,1.09,1570693111,false",
      "255352718,42,3,0.94,0.79,1570693103,false",
      "379724717,23,2,1.01,0.89,1570693115,false",
      "319615710,14,5.5,0.83,0.95,1570693105,false",
      "319615710,22,5.75,0.93,0.85,1570693098,false"
    ],
    "handicapHalf": [
      "255352718,42,-0.25,1.02,0.76,1570693103",
      "207615717,24,1.25,0.95,0.89,1570693096",
      "319615710,22,2.5,0.90,0.88,1570693098",
      "211715713,47,1,0.75,1.07,1570693112",
      "319715711,24,0.25,0.89,0.95,1570693096",
      "222266716,31,-0.25,1.03,0.81,1570693115"
    ],
    "overUnderHalf": [
      "391964616,8,1,0.72,1.08,1570693115",
      "319615710,22,2.5,0.76,1.00,1570693098",
      "211715713,47,1.5,1.05,0.76,1570693112",
      "222540812,22,1.25,0.90,0.84,1570693098"
    ]
  }
}

    Introduction
    Related Plans
    Request
    Response
    Example Request
    Example Response 

 Live Odds Changes (All)

Update Time: 2026-04-02 05:16
Introduction

This API endpoint returns all odds that change in the past 20 seconds. You can use it with the Pre-match and In-play Odds (All) endpoint.
Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/all/changes
    Method: GET
    Calls: This interface is limited to 1 second/call;
    Recommend Calls: 2 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
handicap 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is there inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
europeOdds 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHome 	string	
instantDraw 	string	
instantAway 	string	
handicapIndex 	int	There is no multi-odds for europeOdds, and the handicapIndex is all 1.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnder 	string array	
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
handicapHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
inPlay 	boolean	Is it inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
overUnderHalf 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
Odds Type 	smallint	0:Unable to judge
1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/all/changes?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/all/changes?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "495964610,24,0.75,0.67,1.33,false,false,3,1570693403,false",
      "499964614,3,1.25,0.96,0.94,false,true,1,1570693410,false"
    ],
    "europeOdds": [
      "210824713,19,1.83,3.25,4.85,1,1570693440,false",
      "210824713,7,1.75,3.25,4.75,1,1570693440,false",
      "284350819,12,1.7,3.50,4.50,1,1570693440,false"
    ],
    "overUnder": [
      "485968613,22,2.75,1.04,0.83,1,1570693406,false",
      "485968613,22,2.5,0.78,1.09,2,1570693406,false",
      "485968613,31,2.75,1.04,0.86,1,1570693400,false"
    ],
    "handicapHalf": [
      "245074617,24,-0.75,1.33,0.63,false,2,1570693403",
      "485968613,22,0.5,0.94,0.88,false,1,1570693406",
      "485968613,31,0.5,0.95,0.93,false,1,1570693400"
    ],
    "overUnderHalf": [
      "485968613,3,1,0.78,1.02,1,1570693398",
      "485968613,3,1.25,1.20,0.63,2,1570693410"
    ]
  }
}

 Historical Odds (All)

Update Time: 2026-05-16 10:15Change Log
Introduction

• This API endpoint returns the historical initial and final odds data of the multi market of the match.

• The content of the API is consistent with the API [Historical Odds (Main)], and the data of " handicapIndex" = 1 is the data of the main market.

• By default, it returns the match data from GMT+0 0:00 to the currently completed match.

• Data includes: handicap、handicapHalf、europeOdds、overUnder and overUnderHalf.

• Handicap and overUnder description:
-Handicap is an integer multiple of 0.25, 0 means "0 goal", 0.25 means "0/0.5 goal", 0.5 means "0.5 goal", 0.75 means "0.5/1 goal", 1 means "1 goal" , And so on;

• A positive number means the home team's handicap, a negative number means the away team's handicap.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 7: SNAI, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwette, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin, 50:1xbet

• “Whether Closed”only supports some companies:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/all/history
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 10 minute/call
    Parameters: 

Parameter	Value	Required	Description
date	string	false	Get the match data of the specified date, the range is from GMT +0 0:00-23:59;
Support one month of back-checking.

yyyy-MM-dd, se.g. date=2019-08-01
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId.

e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId.

e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed. As for historical odds, the prefix "instant" means the last one before the match.

Parameter	Value	Description
handicap 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is it inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
handicapCount 	int	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
europeOdds 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
handicapIndex 	int	There is no multi-odds for europeOdds, and the handicapIndex is all 1.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
overUnder 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
handicapHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
inPlay 	boolean	Is it inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
overUnderHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/all/history?api_key=<YOUR_API_KEY>&matchId=326192921";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/all/history?api_key=<YOUR_API_KEY>&matchId=326192921

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "213752121,8,-0.25,0.90,0.90,0,0.48,1.60,false,true,1,1,1638394611,true",
      "213752121,14,-0.25,0.98,0.80,0.25,1.46,0.53,false,true,1,3,1638394321,true",
      "213752121,14,-0.5,0.72,1.09,0,0.30,2.45,false,true,2,3,1638394280,false",
      "213752121,14,0,1.29,0.60,0.5,2.50,0.29,false,true,3,3,1638394280,false",
      "213752121,22,-0.5,0.80,0.90,-0.25,0.91,0.79,false,false,1,1,1638385330,false",
      "213752121,31,-0.5,0.80,1.04,0,0.44,1.66,false,true,1,2,1638394660,true",
      "213752121,31,-0.5,0.76,1.08,0.25,2.43,0.25,false,true,2,2,1638394423,false"
    ],
    "europeOdds": [
      "213752121,4,2.70,3.40,2.20,3.20,3.50,1.91,1,1638288841,false",
      "213752121,7,3.20,3.60,1.90,3.15,3.50,1.97,1,1638291540,false",
      "213752121,8,3.20,3.60,1.91,2.75,3.50,2.10,1,1638394739,true",
      "213752121,9,2.88,3.50,2.10,3.10,3.40,2.05,1,1638394774,false"
    ],
    "overUnder": [
      "213752121,4,2.5,0.50,1.45,2.5,0.50,1.45,1,1638279100,false",
      "213752121,4,1.5,0.15,4.00,1.5,0.15,4.00,2,1638279101,false",
      "213752121,4,3.5,1.20,0.60,3.5,1.20,0.60,3,1638279101,false"
    ],
    "handicapHalf": [
      "213752121,8,0,1.08,0.73,0,1.08,0.73,false,1,1638390372",
      "213752121,22,-0.25,0.73,0.94,-0.25,0.66,1.04,false,1,1638387773",
      "213752121,31,-0.25,0.70,1.16,0,0.94,0.90,true,1,1638390551",
      "213752121,31,0,1.42,0.54,-0.25,0.20,2.77,true,2,1638390211",
      "213752121,42,-0.25,0.71,0.94,0,1.02,0.72,true,1,1638390398",
      "213752121,42,0,1.30,0.50,-0.25,0.10,4.14,true,2,1638390368",
      "213752121,42,-0.5,0.48,1.38,0.25,4.91,0.07,true,3,1638390368",
      "213752121,47,-0.25,0.70,1.06,-0.25,0.71,1.18,false,1,1638387845"
    ],
    "overUnderHalf": [
      "213752121,8,1.25,0.93,0.88,1.25,1.00,0.80,1,1638390372",
      "213752121,22,1.25,0.89,0.78,1.25,0.96,0.71,1,1638387773",
      "213752121,31,1.25,0.92,0.90,2.5,3.12,0.18,1,1638390551",
      "213752121,31,1,0.57,1.33,2.75,4.16,0.10,2,1638390369",
      "213752121,42,1.25,0.77,0.87,2.5,3.92,0.13,1,1638390398"
    ]
  }
}

 Future Odds (All)

Update Time: 2026-01-24 01:56
Introduction

• This API endpoint returns all instant odds of all games after 10 days.

• Data includes: handicap、handicapHalf、europeOdds、overUnder and overUnderHalf.

• Handicap and overUnder description:
-Handicap is an integer multiple of 0.25, 0 means "0 goal", 0.25 means "0/0.5 goal", 0.5 means "0.5 goal", 0.75 means "0.5/1 goal", 1 means "1 goal" , And so on;

• A positive number means the home team's handicap, a negative number means the away team's handicap.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 7: SNAI, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwette, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin, 50:1xbet

• “Whether Closed”only supports some companies:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/all/future
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 10 minute/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed, and the prefix "instant" means the live one that will be changed.

Parameter	Value	Description
handicap 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
maintenance 	boolean	The bet may be closed temporarily when the system is being maintained.
inPlay 	boolean	Is there inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
handicapCount 	int	
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
europeOdds 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
handicapIndex 	int	There is no multi-odds for europeOdds, and the handicapIndex is all 1.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
overUnder 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	Is this bet closed?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
close 	boolean	Is this bet closed?
handicapHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
initialHome 	string	
initialAway 	string	
instantHandicap 	string	1 means home team score minus 1.
-1 means home team score add 1.
1.25 means 1/1.5.
instantHome 	string	
instantAway 	string	
inPlay 	boolean	Is there inplay odds?
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
overUnderHalf 	string array 	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
initialHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
initialOver 	string	
initialUnder 	string	
instantHandicap 	string	1 means the total number of goals is 1.
1.25 means 1/1.5.
instantOver 	string	
instantUnder 	string	
handicapIndex 	int	When the handicapIndex is 1, it is the data of the main market.
changeTime 	int	Change time, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/all/future?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/all/future?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "handicap": [
      "495964610,24,0.75,0.67,1.33,false,false,3,1570693403,false",
      "499964614,3,1.25,0.96,0.94,false,true,1,1570693410,false"
    ],
    "europeOdds": [
      "210824713,19,1.83,3.25,4.85,1,1570693440,false",
      "210824713,7,1.75,3.25,4.75,1,1570693440,false",
      "284350819,12,1.7,3.50,4.50,1,1570693440,false"
    ],
    "overUnder": [
      "485968613,22,2.75,1.04,0.83,1,1570693406,false",
      "485968613,22,2.5,0.78,1.09,2,1570693406,false",
      "485968613,31,2.75,1.04,0.86,1,1570693400,false"
    ],
    "handicapHalf": [
      "245074617,24,-0.75,1.33,0.63,false,2,1570693403",
      "485968613,22,0.5,0.94,0.88,false,1,1570693406",
      "485968613,31,0.5,0.95,0.93,false,1,1570693400"
    ],
    "overUnderHalf": [
      "485968613,3,1,0.78,1.02,1,1570693398",
      "485968613,3,1.25,1.20,0.63,2,1570693410"
    ]
  }
}

 European Odds (Halftime)

Update Time: 2026-04-02 05:17
Introduction

• This API endpoint returns half-time European odds data, including pre-match and In-play Odds.

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 4: Ladbrokes, 8: Bet365, 9: William Hill, 12: Easybets, 14: Vcbet, 17: Mansion88, 19: Interwette, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 48: HK Jockey Club, 49:Bwin

Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/european/half
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed, and the prefix "instant" means the live one that will be changed.

Parameter	Value	Description
matchId 	string	
matchTime 	int	Match scheduled time, unix timestamp
leagueName 	string	
homeName 	string	
awayName 	string	
odds 	list	
	oddsId 	string	
changeTime 	int	Change time, unix timestamp
oddsDetail 	string array	Each string contains all parameters below, separated by comma.
	companyId 	int	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
companyName 	string	
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/european/half?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/european/half?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "359250810",
      "matchTime": 1570683600,
      "leagueName": "Fiji cup",
      "homeName": "Ba",
      "awayName": "Labasa FC",
      "odds": [
        {
          "oddsId": "3145713",
          "changeTime": 1570689469,
          "oddsDetail": "8,Bet365              ,2.05,2.4,5,15,4,1.25"
        },
        {
          "oddsId": "3145624",
          "changeTime": 1570686431,
          "oddsDetail": "12,Easybet             ,2,2.5,4.2,9,1.08,10"
        },
        {
          "oddsId": "3145799",
          "changeTime": 1570686488,
          "oddsDetail": "17,Mansion88           ,2.07,2.13,5.1,8.8,1.08,9"
        },
        {
          "oddsId": "3145800",
          "changeTime": 1570686325,
          "oddsDetail": "22,10BET               ,2,2.4,4.9,6.9,1.16,8.25"
        },
        {
          "oddsId": "3145796",
          "changeTime": 1570686473,
          "oddsDetail": "24,12bet               ,2.08,2.21,4.6,9.2,1.07,9.4"
        },
        {
          "oddsId": "3145803",
          "changeTime": 1570686516,
          "oddsDetail": "42,18Bet               ,5.5,1.26,6.5,13,1.04,15"
        }
      ]
    },
    {
      "matchId": "240350811",
      "matchTime": 1570686900,
      "leagueName": "Indonesia Liga 1 Women",
      "homeName": "Persebaya Surabaya (w)",
      "awayName": "Bali United (W)",
      "odds": [
        {
          "oddsId": "3145720",
          "changeTime": 1570689526,
          "oddsDetail": "8,Bet365              ,3.1,2,3.5,34,15,1.03"
        },
        {
          "oddsId": "3145820",
          "changeTime": 1570689529,
          "oddsDetail": "12,Easybet             ,2.9,2.05,3.6,34,15,1.03"
        },
        {
          "oddsId": "3145808",
          "changeTime": 1570689388,
          "oddsDetail": "42,18Bet               ,3,2.05,3.4,34,11,1.05"
        }
      ]
    }
  ]
}

 In-play Odds

Update Time: 2026-04-02 05:17
Introduction

• This API endpoint returns main market in-play odds, including: handicap、europeOdds、overUnder.

• By default, it returns the updated in-play odds data for all matches in the past 3 minutes.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet, 50:1xbet

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.
Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/inplay
    Method: GET
    Calls: This interface is limited to 3 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.

When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.

Get a maximum of 100 at a time.

This parameter supports querying match data within the last 20 days only.
companyId	string	false	Get the data for the specified company.

When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
recordId 	string	
matchId 	string	
matchTime 	int	-1: Half-time
homeScore 	int	
awayScore 	int	
homeRedCount 	int	
awayRedCount 	int	
type 	int	1: Handicap, odds1-3:home win rate, handicap odds,away win rate;
2: Over/Under, odds1-3: Over rate, Over/Under odds, Under rate;
4: 1x2, odds1-3:home win rate,draw, away win rate;
3: All Closing, odds1-3:0
5: 1x2 Closing, odds1-3:0
6: Handicap Closing, odds1-3:0
7:Over/Under Closing, odds1-3:0
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
odds1 	string	
odds2 	string	
odds3 	string	
changeTime 	int	Change time, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/inplay?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/inplay?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "recordId": "614511284",
      "matchId": "359250810",
      "matchTime": 85,
      "homeScore": 0,
      "awayScore": 1,
      "homeRedCount": 0,
      "awayRedCount": 0,
      "type": 4,
      "companyId": "12",
      "odds1": "29",
      "odds2": "6",
      "odds3": "1.13",
      "changeTime": 1570689977
    },
    {
      "recordId": "614511283",
      "matchId": "359250810",
      "matchTime": 86,
      "homeScore": 0,
      "awayScore": 1,
      "homeRedCount": 0,
      "awayRedCount": 0,
      "type": 1,
      "companyId": "24",
      "odds1": "0.56",
      "odds2": "0",
      "odds3": "1.28",
      "changeTime": 1570689975
    },
    {
      "recordId": "614511282",
      "matchId": "359250810",
      "matchTime": 86,
      "homeScore": 0,
      "awayScore": 1,
      "homeRedCount": 0,
      "awayRedCount": 0,
      "type": 1,
      "companyId": "17",
      "odds1": "0.58",
      "odds2": "0",
      "odds3": "1.25",
      "changeTime": 1570689974
    },
    {
      "recordId": "614511281",
      "matchId": "359250810",
      "matchTime": 85,
      "homeScore": 0,
      "awayScore": 1,
      "homeRedCount": 0,
      "awayRedCount": 0,
      "type": 4,
      "companyId": "8",
      "odds1": "29",
      "odds2": "6",
      "odds3": "1.12",
      "changeTime": 1570689971
    }
  ]
}

 In-play Odds (Halftime)

Update Time: 2026-03-23 07:25
Introduction

• This API endpoint returns main market in-play odds, including: handicapHalf、europeOddHalf、overUnderHalf.

• By default, it returns the updated in-play odds data for all matches in the past 3 minutes.

• The company ID corresponds to the company:
1: Macauslot, 3: Crown, 8: Bet365, 12: Easybets, 17: Mansion88, 22: 10BET, 23: 188bet, 24: 12bet, 31: Sbobet, 35: Wewbet, 42: 18bet
Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/inplay/half
    Method: GET
    Calls: This interface is limited to 3 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.

When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.

Get a maximum of 100 at a time.

This parameter supports querying match data within the last 20 days only.
companyId	string	false	Get the data for the specified company.

When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
recordId 	string	
matchId 	string	
matchTime 	int	-1: Half-time
homeScore 	int	
awayScore 	int	
homeRedCount 	int	
awayRedCount 	int	
type 	int	1: Handicap, odds1-3:home win rate, handicap odds,away win rate;
2: Over/Under, odds1-3: Over rate, Over/Under odds, Under rate;
4: 1x2, odds1-3:home win rate,draw, away win rate;
3: All Closing, odds1-3:0
5: 1x2 Closing, odds1-3:0
6: Handicap Closing, odds1-3:0
7:Over/Under Closing, odds1-3:0
companyId 	string	1: Macauslot
3: Crown
4: Ladbrokes
7: SNAI
8: Bet365
9: William Hill
12: Easybets
14: Vcbet
17: Mansion88
19: Interwette
22: 10BET
23: 188bet
24: 12bet
31: Sbobet
35: Wewbet
42: 18bet
48: HK Jockey Club
odds1 	string	
odds2 	string	
odds3 	string	
changeTime 	int	Change time, unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/inplay/half?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/inplay/half?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "recordId": "163491161",
      "matchId": "355981817",
      "matchTime": 6,
      "homeScore": 0,
      "awayScore": 0,
      "homeRedCount": 0,
      "awayRedCount": 0,
      "type": 4,
      "companyId": "17",
      "odds1": "3.7",
      "odds2": "2.21",
      "odds3": "2.34",
      "changeTime": 1574935689
    },
    {
      "recordId": "163491160",
      "matchId": "355981817",
      "matchTime": 6,
      "homeScore": 0,
      "awayScore": 0,
      "homeRedCount": 0,
      "awayRedCount": 0,
      "type": 2,
      "companyId": "17",
      "odds1": "1.01",
      "odds2": "1.25",
      "odds3": "0.75",
      "changeTime": 1574935689
    }
  ]
}

 Odd Modify Record

Update Time: 2022-06-21 10:52Change Log
Introduction

• With parameters: type=match, returns a list of matches with historical odds that may have increased or decreased in the last hour.

• With parameters:matchId=matchID&companyID=[companyID],returns historical odds by match ID (main market).
eg.http://api.isportsapi.com/sport/football/odds/oddsbyid?api_key&matchId=256921227&companyID=3

• With parameters:type=multi&matchId=matchID&companyID=[companyID],returns historical odds by match ID (multi market).
eg.http://api.isportsapi.com/sport/football/odds/oddsbyid?api_key&type=multi&matchId=256921227&companyID=3
Related Plans

You can use this api by subscribing plans:  Odds,  Odds Pro.
Request

    Path: /sport/football/odds/oddsbyid
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 20 second/call
    Parameters: 

Parameter	Value	Required	Description
type=match	string 	true	A list of matches with historical odds that may have increased or decreased in the last hour.
matchId=matchID&companyID=[companyID]	string 	true	Get historical odds by match ID (main market).
type=multi&matchId=matchID&companyID=[companyID]	string 	true	Get historical odds by match ID (multi market).
Response

Parameter	Value	Description
list 	list	Add "type=match" parameter description.

	matchId 	string	
companyId 	string	When it is 0, it means that all odds for the match are cleared.
operateTime 	int	
handicap 	string array	
	companyID 	string	
num 	int	Handicap serial number, main market interface does not have this item.
odds1 	string	initialHandicap
odds2 	string	initialHome
odds3 	string	initialAway
odds4 	string	instantHandicap
odds5 	string	instantHome
odds6 	string	instantAway
modifyTime 	int	
detail 	object	
	id 	string	
odds1 	string	handicap odds
odds2 	string	home win rate
odds3 	string	away win rate
modifyTime 	int	
type 	smallint	Dedicated to multi market interface.

1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
isEarly 	boolean	Dedicated to main market interface.

Is it early?
overUnder 	string array	
	companyID 	string	
num 	int	Handicap serial number, main market interface does not have this item.
odds1 	string	initialHandicap
odds2 	string	initialOver
odds3 	string	initialUnder
odds4 	string	instantHandicap
odds5 	string	instantOver
odds6 	string	instantUnder
modifyTime 	int	
detail 	object	
	id 	string	
odds1 	string	Over/Under odds
odds2 	string	Over rate
odds3 	string	Under rate
modifyTime 	int	
type 	smallint	Dedicated to multi market interface.

1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
isEarly 	boolean	Dedicated to main market interface.

Is it early?
europe 	string array	
	companyID 	string	
odds1 	string	initialHome
odds2 	string	initialDraw
odds3 	string	initialAway
odds4 	string	instantHome
odds5 	string	instantDraw
odds6 	string	instantAway
modifyTime 	int	
detail 	object	
	id 	string	
odds1 	string	home win rate
odds2 	string	draw rate
odds3 	string	away win rate
modifyTime 	int	
isEarly 	boolean	Is it early?
halfHandicap 	string array	
	companyID 	string	
num 	int	Handicap serial number, main market interface does not have this item.
odds1 	string 	initialHandicap
odds2 	string 	initialHome
odds3 	string 	initialAway
odds4 	string 	instantHandicap
odds5 	string 	instantHome
odds6 	string 	instantAway
modifyTime 	int	
detail 	object	
	id 	string	
odds1 	string 	handicap odds
odds2 	string 	home win rate
odds3 	string 	away win rate
modifyTime 	int	
type 	smallint	Dedicated to multi market interface.

1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
isEarly 	boolean	Dedicated to main market interface.

Is it early?
halfOverUnder 	string array	
	companyID 	string	
num 	int	Handicap serial number, main market interface does not have this item.
odds1 	string	initialHandicap
odds2 	string	initialOver
odds3 	string	initialUnder
odds4 	string	instantHandicap
odds5 	string	instantOver
odds6 	string	instantUnder
modifyTime 	int	
detail 	object	
	id 	string	
odds1 	string	Over/Under odds
odds2 	string	Over rate
odds3 	string	Under rate
modifyTime 	int	
type 	smallint	Dedicated to multi market interface.

1:Early Odds
2:Instant odds(after the early odds before the match)
3:Inplay odds
isEarly 	boolean	Dedicated to main market interface.

Is it early?
halfEurope 	string array	
	companyID 	string	
odds1 	string 	initialHome
odds2 	string 	initialDraw
odds3 	string 	initialAway
odds4 	string 	instantHome
odds5 	string 	instantDraw
odds6 	string 	instantAway
modifyTime 	int	
detail 	object	
	id 	string	
odds1 	string 	home win rate
odds2 	string 	draw rate
odds3 	string 	away win rate
modifyTime 	int	
isEarly 	boolean	Is it early?
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/oddsbyid?api_key=<YOUR_API_KEY>&type=match";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/oddsbyid?api_key=<YOUR_API_KEY>&type=match

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "204931221",
      "companyId": "47",
      "operateTime": 1655457984
    },
    {
      "matchId": "232911220",
      "companyId": "4",
      "operateTime": 1655455008
    }
  ]
}

 European Odds (200+ Bookmakers)

Update Time: 2026-04-02 04:18
Introduction

• This API endpoint returns European odds of more than 200 companies.

• Important: To ensure consistent results, use only one of the following primary filters per request: matchId (single match), date (specific calendar day), day (next N days), or min (recent updates). These parameters are mutually exclusive and should not be combined, though companyId may be used alongside any of them to filter specific operators.

• Default returns the match data within one day.

• Tips: You have access to this API and all APIs in Odds (18 Agencies) when subscribing the Odds Pro. But notice that company IDs in this API are different from other odds APIs.

• Win rate: return rate calculation method:
- Home win rate = 1/(1 + home win odds/draw win odds+ home win odds /away win odds)*100%
- Draw win rate = 1/(1+draw win odds/home win odds+draw win odds/away win odds)*100%
- Away win rate=1/(1+away win odds/home win odds+away win odds/draw win odds)*100%
- Return rate=home win rate*home win odds

• Kelly index calculation method:
- Calculate the average odds of the game first, then calculate the average winning percentage
- Home=home win odds*average home win rate
- Draw=draw win odds*average draw win rate
- Away=away win odds*average away win rate
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/european/all
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 90 second/call
    Parameters: 

Parameter	Value	Required	Description
day	string	false	Returns the odds of the specified days. Such as day=1, day is 1-3，Use [date] more often.
date	string	false	yyyy-mm-dd, such as date=2019-08-01
Support one month of back-checking.
min	string	false	Returns the odds of the specified minutes.
min=5, get change data for the past 5 minutes (recommended)
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
Get a maximum of 100 at a time.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

    The prefix "initial" means the first one that won't be changed, and the prefix "instant" means the live one that will be changed. As for historical odds, the prefix "instant" returns the last one before the match.

Parameter	Value	Description
matchId 	string	
matchTime 	int	Match scheduled time, unix timestamp
leagueName 	string	
homeName 	string	
awayName 	string	
odds 	list	
	oddsId 	string	
changeTime 	int	Change time, unix timestamp
oddsDetail 	string array 	Each string contains all parameters below, separated by comma.
	companyId 	int	
companyName 	string	
initialHome 	string	
initialDraw 	string	
initialAway 	string	
instantHome 	string	
instantDraw 	string	
instantAway 	string	
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/european/all?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/european/all?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "233350813",
      "matchTime": 1570694400,
      "leagueName": "Indonesia Liga 3",
      "homeName": "Prima Con FC",
      "awayName": "PSIT Kota Cirebon",
      "odds": [
        {
          "oddsId": "90797951",
          "changeTime": 1570684680,
          "oddsDetail": "777,1Bet,2.1,3.25,3,1.95,3.15,3.5"
        },
        {
          "oddsId": "90797715",
          "changeTime": 1570678560,
          "oddsDetail": "281,Bet 365,2.1,3.25,3,,,"
        },
        {
          "oddsId": "90799427",
          "changeTime": 1570687320,
          "oddsDetail": "90,Easybets,2.1,3.2,3,2.1,3.2,3"
        },
        {
          "oddsId": "90797914",
          "changeTime": 1570687140,
          "oddsDetail": "1229,22Bet,2.12,3.24,2.99,2.12,3.22,3"
        },
        {
          "oddsId": "90797913",
          "changeTime": 1570687380,
          "oddsDetail": "1047,1xBet,2.12,3.24,2.99,2.12,3.24,2.99"
        }
      ]
    },
    {
      "matchId": "243350814",
      "matchTime": 1570694400,
      "leagueName": "Indonesia Liga 3",
      "homeName": "PSGJ Kabupaten Cirebon",
      "awayName": "Perses Sumedang",
      "odds": [
        {
          "oddsId": "90797962",
          "changeTime": 1570683840,
          "oddsDetail": "777,1Bet,2.15,3.8,2.6,2.3,3.7,2.45"
        },
        {
          "oddsId": "90797716",
          "changeTime": 1570678560,
          "oddsDetail": "281,Bet 365,2.15,3.75,2.6,,,"
        },
        {
          "oddsId": "90799426",
          "changeTime": 1570687320,
          "oddsDetail": "90,Easybets,2.15,3.8,2.6,2.15,3.8,2.6"
        },
        {
          "oddsId": "90797944",
          "changeTime": 1570684020,
          "oddsDetail": "1229,22Bet,2.17,3.74,2.59,2.16,3.74,2.6"
        },
        {
          "oddsId": "90797941",
          "changeTime": 1570684200,
          "oddsDetail": "1047,1xBet,2.17,3.74,2.59,2.16,3.74,2.6"
        }
      ]
    }
  ]
}

OTHER ODDS!

 Corners 1x2(pre-match)

Update Time: 2026-01-29 04:58Change Log
Introduction

This API endpoint returns pre-match odds for Corners 1X2, where the result (home / draw / away) is determined by the total number of corners taken by each team during the match.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/corners1x2/prematch
    Method: GET
    Calls: 

Response

Parameter	Value	Description
matchId 	string	
companyId 	string	3: Crown
odds 	object	
	home 	string	
draw 	string	
away 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/corners1x2/prematch?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/corners1x2/prematch?api_key=<YOUR_API_KEY>

{
"code": 0,

  "message": "success",

  "data": [
    {

      "matchId": "367027822",

      "companyId": "3",

      "odds": {

        "home": "2.01",

        "draw": "7.3",

        "away": "2.05"
      
},

      "changeTime": 1769559908
    
},

    {

      "matchId": "322754820",

      "companyId": "3",

      "odds": {

        "home": "1.51",

        "draw": "8.2",

        "away": "3"
      
},

      "changeTime": 1769561076
}

 Team Goals

Update Time: 2026-01-29 04:59Change Log
Introduction

This API endpoint returns the odds for Team Goals (Over/Under).
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/teamGoals
    Method: GET
    Calls: This interface is limited to 10 seconds/call
    Recommend Calls: 15 seconds/call

Response

Parameter	Value	Description
matchId 	string	
companyId 	string	3: Crown
home 	object	
	total 	string	
over 	string	
under 	string	
away 	object	
	total 	string	
over 	string	
under 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/teamGoals?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/teamGoals?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "327841923",
      "companyId": "3",
      "home": {
        "total": "1.75",
        "over": "0.95",
        "under": "0.87"
      },
      "away": {
        "total": "0.75",
        "over": "0.7",
        "under": "1.12"
      },
      "changeTime": 1769558155
    },
    {
      "matchId": "392152920",
      "companyId": "3",
      "home": {
        "total": "0.5",
        "over": "0.74",
        "under": "1.08"
      },
      "away": {
        "total": "3",
        "over": "1.01",
        "under": "0.81"
      },
      "changeTime": 1769556299
    },
    {
      "matchId": "282051927",
      "companyId": "3",
      "home": {
        "total": "2.25",
        "over": "0.9",
        "under": "0.92"
      },
      "away": {
        "total": "0.5",
        "over": "0.83",
        "under": "0.99"
      },
      "changeTime": 1769540017
    },
    {
      "matchId": "217027827",
      "companyId": "3",
      "home": {
        "total": "1.25",
        "over": "1.05",
        "under": "0.77"
      },
      "away": {
        "total": "1.5",
        "over": "1.01",
        "under": "0.81"
      },
      "changeTime": 1766467094
    }
  ]
}

 Both Teams to Score

Update Time: 2026-03-04 04:22Change Log
Introduction

This API endpoint returns the odds for Both Teams to Score, based on whether both the home and away teams score at least one goal during the match.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/bothScore
    Method: GET
    Calls: This interface is limited to 10 seconds/call
    Recommend Calls: 15 seconds/call

Response

Parameter	Value	Description
matchId 	string	
companyId 	string	4: Ladbrokes
8: Bet365
9: William Hill
19: Interwetten
31: Sbobet
49:Bwin
yes 	string	
no 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/bothScore?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/bothScore?api_key=<YOUR_API_KEY>

{

"code":0,

"message":"success",

"data":[{

"matchId":"396113921",

"companyId":"4",

"yes":"0.3",

"no":"2.2""changeTime":1769590753

},

{

"matchId":"396113921",

"companyId":"9",

"yes":"0.222",

"no":"1.2""changeTime":1769586748

}

 Card

Update Time: 2026-01-29 07:26Change Log
Introduction

This API interface returns the odds for Cards markets, including standard (1X2), handicap, and total (Over/Under), based on the number of cards shown during the match.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/card
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 15 second/call

Response

Parameter	Value	Description
standard 	object	Standard card market data (1X2), based on the comparison of cards shown to each team.
	matchId 	string	
companyId 	string	3: Crown
odds 	object	
	home 	string	Odds for the home team receiving more cards than the away team.
draw 	string	Odds for both teams receiving the same number of cards.
away 	string	Odds for the away team receiving more cards than the home team.
changeTime 	int	Unix timestamp
handciap 	object	Handicap card market data, where a handicap value is applied to the card count.
	matchId 	string	
companyId 	string	
odds 	object	Odds for the handicap cards market.
changeTime 	int	Unix timestamp
total 	object	Total cards market data based on Over / Under outcomes.
	matchId 	string	
companyId 	string	
odds 	object	Odds for the total cards (Over/Under) market.
	total 	string	Card line value (e.g. 3.5, 4.5).
over 	string	Odds for the total number of cards being over the line.
under 	string	Odds for the total number of cards being under the line.
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/card?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/card?api_key=<YOUR_API_KEY>

{
"code": 0,

  "message": "success",

  "data": {

    "standard": [
      {

        "matchId": "237016827",

        "companyId": "3",

        "odds": {

          "home": "2.59",

          "draw": "3.8",

          "away": "2.12"
        
},

        "changeTime": 1769550780
      
},

      {

        "matchId": "208016825",

        "companyId": "3",

        "odds": {

          "home": "2.69",

          "draw": "3.9",

          "away": "2.03"
        
},

        "changeTime": 1769549203
}

 Number of Goals in Match (pre-match)

Update Time: 2022-09-01 10:30
Introduction

• This API endpoint returns the pre-match odds for the number of goals in the match.

• By default, returns data for the next 10 days.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/totalgoals/prematch
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
matchId 	string	
companyId 	string	1: Macauslot
3: Crown
odds 	object	
	zeroToOne 	string	
twoToThree 	string	
fourToSix 	string	
moreThanSix 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/totalgoals/prematch?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/totalgoals/prematch?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "213671817",
      "companyId": "3",
      "odds": {
        "zeroToOne": "",
        "twoToThree": "",
        "fourToSix": "",
        "moreThanSix": ""
      },
      "changeTime": 1574835984
    },
    {
      "matchId": "223671818",
      "companyId": "3",
      "odds": {
        "zeroToOne": "",
        "twoToThree": "",
        "fourToSix": "",
        "moreThanSix": ""
      },
      "changeTime": 1574836325
    },
    {
      "matchId": "366291813",
      "companyId": "3",
      "odds": {
        "zeroToOne": "",
        "twoToThree": "",
        "fourToSix": "",
        "moreThanSix": ""
      },
      "changeTime": 1574836654
    },
    {
      "matchId": "214391817",
      "companyId": "3",
      "odds": {
        "zeroToOne": "",
        "twoToThree": "",
        "fourToSix": "",
        "moreThanSix": ""
      },
      "changeTime": 1574844118
    }
  ]
}

 Correct Score (pre-match)

Update Time: 2022-09-01 10:31
Introduction

• This API endpoint returns the pre-match odds for the correct score.

• By default, returns data for the next 10 days.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/score/prematch
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
matchId 	string	
companyId 	string	1: Macauslot
3: Crown
odds 	object	
	bettingOddsItems 	list	
	homeScore 	int	
awayScore 	int	
odds 	string	
otherScoresOdds 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/score/prematch?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/score/prematch?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "202865719",
      "companyId": "3",
      "odds": {
        "bettingOddsItems": [
          {
            "homeScore": 1,
            "awayScore": 0,
            "odds": "8.9"
          },
          {
            "homeScore": 2,
            "awayScore": 0,
            "odds": "10.5"
          },
          {
            "homeScore": 2,
            "awayScore": 1,
            "odds": "8"
          },
          {
            "homeScore": 3,
            "awayScore": 0,
            "odds": "17.5"
          },
          {
            "homeScore": 3,
            "awayScore": 1,
            "odds": "13.5"
          },
          {
            "homeScore": 3,
            "awayScore": 2,
            "odds": "21"
          },
          {
            "homeScore": 4,
            "awayScore": 0,
            "odds": "41"
          },
          {
            "homeScore": 4,
            "awayScore": 1,
            "odds": "31"
          },
          {
            "homeScore": 4,
            "awayScore": 2,
            "odds": "46"
          },
          {
            "homeScore": 4,
            "awayScore": 3,
            "odds": "101"
          },
          {
            "homeScore": 0,
            "awayScore": 0,
            "odds": "16"
          },
          {
            "homeScore": 1,
            "awayScore": 1,
            "odds": "7"
          },
          {
            "homeScore": 2,
            "awayScore": 2,
            "odds": "12.5"
          },
          {
            "homeScore": 3,
            "awayScore": 3,
            "odds": "46"
          },
          {
            "homeScore": 4,
            "awayScore": 4,
            "odds": "201"
          },
          {
            "homeScore": 0,
            "awayScore": 1,
            "odds": "12"
          },
          {
            "homeScore": 0,
            "awayScore": 2,
            "odds": "19"
          },
          {
            "homeScore": 1,
            "awayScore": 2,
            "odds": "11"
          },
          {
            "homeScore": 0,
            "awayScore": 3,
            "odds": "41"
          },
          {
            "homeScore": 1,
            "awayScore": 3,
            "odds": "26"
          },
          {
            "homeScore": 2,
            "awayScore": 3,
            "odds": "31"
          },
          {
            "homeScore": 0,
            "awayScore": 4,
            "odds": "121"
          },
          {
            "homeScore": 1,
            "awayScore": 4,
            "odds": "71"
          },
          {
            "homeScore": 2,
            "awayScore": 4,
            "odds": "81"
          },
          {
            "homeScore": 3,
            "awayScore": 4,
            "odds": "131"
          }
        ],
        "otherScoresOdds": "17.5"
      },
      "changeTime": 1574844711
    }
  ]
}

 Half Time Correct Score (pre-match)

Update Time: 2022-09-01 10:31
Introduction

• This API endpoint returns the pre-match odds for the half time correct score.

• By default, returns data for the next 10 days.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/score/half/prematch
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
Response

Parameter	Value	Description
matchId 	string	
companyId 	string	1: Macauslot
3: Crown
odds 	object	
	bettingOddsItems 	list	
	homeScore 	int	
awayScore 	int	
odds 	string	
otherScoresOdds 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/score/half/prematch?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/score/half/prematch?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "202865719",
      "companyId": "3",
      "odds": {
        "bettingOddsItems": [
          {
            "homeScore": 1,
            "awayScore": 0,
            "odds": "3.5"
          },
          {
            "homeScore": 2,
            "awayScore": 0,
            "odds": "8.8"
          },
          {
            "homeScore": 2,
            "awayScore": 1,
            "odds": "16"
          },
          {
            "homeScore": 3,
            "awayScore": 0,
            "odds": "31"
          },
          {
            "homeScore": 3,
            "awayScore": 1,
            "odds": "56"
          },
          {
            "homeScore": 3,
            "awayScore": 2,
            "odds": "151"
          },
          {
            "homeScore": 4,
            "awayScore": 0,
            "odds": "0"
          },
          {
            "homeScore": 4,
            "awayScore": 1,
            "odds": "0"
          },
          {
            "homeScore": 4,
            "awayScore": 2,
            "odds": "0"
          },
          {
            "homeScore": 4,
            "awayScore": 3,
            "odds": "0"
          },
          {
            "homeScore": 0,
            "awayScore": 0,
            "odds": "2.77"
          },
          {
            "homeScore": 1,
            "awayScore": 1,
            "odds": "6.3"
          },
          {
            "homeScore": 2,
            "awayScore": 2,
            "odds": "51"
          },
          {
            "homeScore": 3,
            "awayScore": 3,
            "odds": "151"
          },
          {
            "homeScore": 4,
            "awayScore": 4,
            "odds": "0"
          },
          {
            "homeScore": 0,
            "awayScore": 1,
            "odds": "4.95"
          },
          {
            "homeScore": 0,
            "awayScore": 2,
            "odds": "17.5"
          },
          {
            "homeScore": 1,
            "awayScore": 2,
            "odds": "21"
          },
          {
            "homeScore": 0,
            "awayScore": 3,
            "odds": "81"
          },
          {
            "homeScore": 1,
            "awayScore": 3,
            "odds": "96"
          },
          {
            "homeScore": 2,
            "awayScore": 3,
            "odds": "151"
          },
          {
            "homeScore": 0,
            "awayScore": 4,
            "odds": "0"
          },
          {
            "homeScore": 1,
            "awayScore": 4,
            "odds": "0"
          },
          {
            "homeScore": 2,
            "awayScore": 4,
            "odds": "0"
          },
          {
            "homeScore": 3,
            "awayScore": 4,
            "odds": "0"
          }
        ],
        "otherScoresOdds": "61"
      },
      "changeTime": 1574844594
    }
  ]
}

 Total Corners (pre-match)

Update Time: 2026-01-24 01:58Change Log
Introduction

• This API endpoint returns the pre-match odds for the total corners.

• By default, returns data for the next 10 days.
Related Plans

You can use this api by subscribing plans:  Odds Pro.
Request

    Path: /sport/football/odds/cornerstotal/prematch
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 15 second/call
    Parameters: 

Parameter	Value	Required	Description
matchId	string	false	Get the data for the specified match.
When multiple matches are acquired at the same time, use "," to separate the matchId. e.g. matchId=322964610,322964611.
companyId	string	false	Get the data for the specified company.
When multiple companies are acquired at the same time, use "," to separate the companyId. e.g. companyId=3,8.
cmd	string，rule	false	Format:cmd=half
Get half time total odds of corner.
Response

Parameter	Value	Description
matchId 	string	
companyId 	string	3: Crown
8: Bet365
odds 	object	
	totalCorners 	string	
over 	string	
under 	string	
changeTime 	int	Unix timestamp
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/football/odds/cornerstotal/prematch?api_key=<YOUR_API_KEY>";

    // Call iSport Api to get data in json format
    String charset = "UTF-8";
    String jsonResult = get(url, charset);

        System.out.println(jsonResult);
  }

  /**
   * @param url
   * @param charset
   * @return return json string
   */
  public static String get(String url, String charset) {
    BufferedReader reader = null;
    String result = null;
    StringBuffer sbf = new StringBuffer();
    String userAgent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36";
    try {
      URL newUrl = new URL(url);
      HttpURLConnection connection = (HttpURLConnection)newUrl.openConnection();
      connection.setRequestMethod("GET");
      connection.setReadTimeout(30000);
      connection.setConnectTimeout(30000);
      connection.setRequestProperty("User-agent", userAgent);
      connection.connect();
      InputStream is = connection.getInputStream();
      reader = new BufferedReader(new InputStreamReader(is, charset));
      String strRead = null;
      while ((strRead = reader.readLine()) != null) {
        sbf.append(strRead);
        sbf.append("\r\n");
      }
      reader.close();
      result = sbf.toString();
    } catch (Exception e) {
      e.printStackTrace();
    }
    return result;
  }
}

Example Response
http://api.isportsapi.com/sport/football/odds/cornerstotal/prematch?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "366291813",
      "companyId": "8",
      "odds": {
        "totalCorners": "9.5",
        "over": "0.98",
        "under": "0.82",
        "close": false
      },
      "changeTime": 1574810912
    },
    {
      "matchId": "390990715",
      "companyId": "8",
      "odds": {
        "totalCorners": "9.5",
        "over": "0.95",
        "under": "0.85",
        "close": false
      },
      "changeTime": 1574805954
    },
    {
      "matchId": "210596618",
      "companyId": "3",
      "odds": {
        "totalCorners": "10",
        "over": "0.9",
        "under": "0.9",
        "close": false
      },
      "changeTime": 1574842268
    }
  ]
}