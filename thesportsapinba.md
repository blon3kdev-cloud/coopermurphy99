 Schedule & Results (Basic)

Update Time: 2026-04-02 05:20Change Log
Introduction

• This API endpoint returns the basic information of the match.

• The request path needs at least one parameter (date, leagueId, and matchId ) to retrieve correct response. These three parameters can not be used at the same time.

• You can use it with the Match Modify Record endpoint.

• Tips: You have access to all the basketball Common API endpoints with any valid paid basketball plans.
Related Plans

You can use this api by subscribing plans:  Live Data,  Stats,  Odds.
Request

    Path: /sport/basketball/schedule/basic
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 12 hour/call
    Parameters: 

Parameter	Value	Required	Description
date	string	false	yyyy-MM-dd, e.g. 2019-08-01.
leagueId	string	false	
season	string	false	Use with leagueID to get the specified season, e.g. 18-19.
Return to the current season by default
matchId 	string	false	Support querying the current season's matches.
Response

Parameter	Value	Description
matchId 	string	
leagueId 	string	
leagueName 	string	Short name, e.g. NBA.
quarterCount 	int	2: the match has 2 quarter
4: the match has 4 quarter
matchTime 	int	Match scheduled time, unix timestamp
status 	int	0: Not started
1: The first quarter
2: The second quarter
3: The third quarter
4: The fourth quarter
5: The first OT
6: The second OT
7: The third OT
50: Half-time
-1: Finished
-2: TBD
-3: Interrupted
-4: Cancelled
-5: Postponed
homeId 	string	
homeName 	string	
awayId 	string	
awayName 	string	
homeScore 	int	
awayScore 	int	
explain 	string	Return to the live text of the match, e.g. [Spurs][SAS] Team Timeout: Regular.
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
    String url = "http://api.isportsapi.com/sport/basketball/schedule/basic?api_key=<YOUR_API_KEY>&leagueId=111";

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
http://api.isportsapi.com/sport/basketball/schedule/basic?api_key=<YOUR_API_KEY>&leagueId=111

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "29532537",
      "leagueId": "122",
      "leagueName": "WNBA",
      "quarterCount": 4,
      "matchTime": 1557442800,
      "status": -1,
      "homeName": "New York Liberty",
      "awayName": "China (w)",
      "homeScore": 89,
      "awayScore": 71,
      "explain": "",
      "neutral": false
    },
    {
      "matchId": "10632539",
      "leagueId": "122",
      "leagueName": "WNBA",
      "quarterCount": 4,
      "matchTime": 1557532800,
      "status": -1,
      "homeName": "Minnesota Lynx",
      "awayName": "Washington Mystics",
      "homeScore": 86,
      "awayScore": 79,
      "explain": "",
      "neutral": false
    },
    {
      "matchId": "21632530",
      "leagueId": "122",
      "leagueName": "WNBA",
      "quarterCount": 4,
      "matchTime": 1557626400,
      "status": -1,
      "homeName": "Phoenix Mercury",
      "awayName": "Los Angeles Sparks",
      "homeScore": 82,
      "awayScore": 75,
      "explain": "",
      "neutral": false
    }
  ]
}

 Schedule & Results

Update Time: 2026-04-02 05:22Change Log
Introduction

• This API endpoint allows you to get the schedule and results of basketball matches with the corresponding date ( from the last two months to the future ) or leagueId.

• The request path needs at least one parameter (date, leagueId, and matchId ) to retrieve the correct response. These three parameters can not be used at the same time.

• You can use it with the Match Modify Record endpoint.
Related Plans

You can use this api by subscribing plans:  Live Data.
Request

    Path: /sport/basketball/schedule
    Method: GET
    Calls: This interface is limited to 60 second/call;
    Recommend Calls: 12 hour/call
    Parameters: 

Parameter	Value	Required	Description
date	string	false	match data for the specified time: GMT +0 00:00-23:59.

yyyy-MM-dd, e.g. 2019-08-01.
leagueId	string	false	Get the schedule data of the current season of the specified event.
season	string	false	Use with leagueID to get the specified season, e.g. 18-19.
Return to the current season by default.
matchId	string	false	Get match data for the specified match.
Response

Parameter	Value	Description
matchId 	string	
leagueId 	string	
leagueName 	string	Short name, e.g. NBA.
quarterCount 	int	2: the match has 2 quarter
4: the match has 4 quarter
matchTime 	int	Match scheduled time, unix timestamp
status 	int	0: Not started
1: The first quarter
2: The second quarter
3: The third quarter
4: The fourth quarter
5: The first OT
6: The second OT
7: The third OT
50: Half-time
-1: Finished
-2: TBD
-3: Interrupted
-4: Cancelled
-5: Postponed
quarterRemainTime 	string	Rest time of the quarter, e.g. 01:23
homeId 	string	
homeName 	string	
homeRank 	int	League ranking of home team
awayId 	string	
awayName 	string	
awayRank 	int	League ranking of away team
homeScore 	int	Total score of home team
awayScore 	int	Total score of away team
homeFirstQuarterScore 	int	
awayFirstQuarterScore 	int	
homeSecondQuarterScore 	int	
awaySecondQuarterScore 	int	
homeThirdQuarterScore 	int	
awayThirdQuarterScore 	int	
homeFourthQuarterScore 	int	
awayFourthQuarterScore 	int	
overTimeCount 	int	Number of overtime
homeFirstOverTimeScore 	int	
awayFirstOverTimeScore 	int	
homeSecondOverTimeScore 	int	
awaySecondOverTimeScore 	int	
homeThirdOverTimeScore 	int	
awayThirdOverTimeScore 	int	
leagueSeason 	string	Season of league
matchType 	int	1: Regular season
2: Post season
3: Pre-season
- 1: Unclassified
playoffsId 	string	Only the playoffs have data.
stageId 	string	Only the cups have data.
hasStats 	boolean	Is there stats data?
explain 	string	Return to the live text of the match, e.g. [Spurs][SAS] Team Timeout: Regular.
roundType 	string	For cups, e.g. Groups
For league playoffs, e.g. Western 1 Round
group 	string	Group name of the cup, e.g. A.
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
    String url = "http://api.isportsapi.com/sport/basketball/schedule?api_key=<YOUR_API_KEY>&leagueId=111";

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
http://api.isportsapi.com/sport/basketball/schedule?api_key=<YOUR_API_KEY>&leagueId=111

{
  "code": 0,
  "message": "success",
  "data": [
    {
      "matchId": "29532537",
      "leagueId": "122",
      "leagueName": "WNBA",
      "quarterCount": 4,
      "matchTime": 1557442800,
      "status": -1,
      "quarterRemainTime": "",
      "homeId": "68",
      "homeName": "New York Liberty",
      "homeRank": 5,
      "awayId": "2006",
      "awayName": "China (w)",
      "awayRank": 0,
      "homeScore": 89,
      "awayScore": 71,
      "homeFirstQuarterScore": 18,
      "awayFirstQuarterScore": 16,
      "homeSecondQuarterScore": 18,
      "awaySecondQuarterScore": 26,
      "homeThirdQuarterScore": 25,
      "awayThirdQuarterScore": 13,
      "homeFourthQuarterScore": 28,
      "awayFourthQuarterScore": 16,
      "overTimeCount": 0,
      "homeFirstOverTimeScore": 0,
      "awayFirstOverTimeScore": 0,
      "homeSecondOverTimeScore": 0,
      "awaySecondOverTimeScore": 0,
      "homeThirdOverTimeScore": 0,
      "awayThirdOverTimeScore": 0,
      "leagueSeason": "19",
      "matchType": 3,
      "hasStats": true,
      "explain": "",
      "roundType": "",
      "group": "",
      "neutral": false
    }
  ]
}

 Pre-match and In-play Odds

Update Time: 2026-04-02 05:25
Introduction

• This API endpoint returns odds of basketball match, including Spread, Money Line, Total.

• Return to the unplayed and in-play matches, including pre-match and In-play Odds

• Odds type corresponds to company ID and company name:
- Spread/Money Line（1x2 Odds）
1: Marcauslot；2: Easybet；3: Crown；8: Bet365；9：Vcbet；10： William Hill；19：Interwetten；20：Ladbrokes；31: Sbobet ；24: 12bet; 30：China Sports Lottery; 49:BWin
- Total
4：Marcauslot；5: Easybet；6：Crown；11:Bet365；12：Vcbet；13： William Hill；22：Interwetten；23：Ladbrokes；34:Sbobet；27:12bett; 33: China Sports Lottery; 52: BWin

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.
Related Plans

You can use this api by subscribing plans:  Odds.
Request

    Path: /sport/basketball/odds/fulltime
    Method: GET
    Calls: This interface is limited to 10 second/call;
    Recommend Calls: 1 minute/call

Response

Parameter	Value	Description
spread 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	Company id for Spread:
1: Macauslot
2: Easybets
3: Crown
8: Bet365
9: Vcbet
10:William Hill
19:Interwetten
20:Ladbrokes
31:Sbobet
24: 12bet
30:China Sports Lottery
49:BWin
initialHandicap 	string	
initialHome 	string	
initialAway 	string	
instantHandicap 	string	instant odds, excluding inPlay odds.
instantHome 	string	instant odds, excluding inPlay odds.
instantAway 	string	instant odds, excluding inPlay odds.
inPlayHandicap 	string	
inPlayHome 	string	
inPlayAway 	string	
moneyLine 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	Company id for moneyLine:
1: Macauslot
2: Easybets
3: Crown
8: Bet365
9: Vcbet
10:William Hill
19:Interwetten
20:Ladbrokes
31:Sbobet
24: 12bet
30:China Sports Lottery
49:BWin
initialHome 	string	
initialAway 	string	
instantHome 	string	instant odds, excluding inPlay odds.
instantAway 	string	instant odds, excluding inPlay odds.
total 	string array	Each string contains all parameters below, separated by comma.
	matchId 	string	
companyId 	string	Company id for total:
4: Macauslot
5: Easybets
6: Crown
11: Bet365
12: Vcbet
13:William Hill
22:Interwetten
23:Ladbrokes
34::Sbobet
27:12bet
33:China Sports Lottery
52:BWin
initialTotal 	string	
initialOver 	string	
initialUnder 	string	
instantTotal 	string	instant odds, excluding inPlay odds.
instantOver 	string	instant odds, excluding inPlay odds.
instantUnder 	string	instant odds, excluding inPlay odds.
inPlayTotal 	string	
inPlayOver 	string	
inPlayUnder 	string	
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/basketball/odds/fulltime?api_key=<YOUR_API_KEY>";

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
http://api.isportsapi.com/sport/basketball/odds/fulltime?api_key=<YOUR_API_KEY>

{
  "code": 0,
  "message": "success",
  "data": {
    "spread": [
      "22548537,1,-6.5,0.80,0.90,-5.5,0.84,0.86,-5.5,0.84,0.86",
      "22548537,2,-6,0.96,0.90,-6,0.86,1.01,-6,0.86,1.01",
      "22548537,3,-6,0.901,0.899,-5.5,0.876,0.924,-5.5,0.876,0.924",
      "22548537,8,-7,0.90,0.90,-6,0.90,0.90,-6,0.90,0.90"
    ],
    "moneyLine": [
      "22548537,2,3.00,1.34,3.20,1.23",
      "22548537,9,3.125,1.333,2.80,1.40",
      "22548537,8,3.50,1.32,3.15,1.38",
      "22548537,1,2.95,1.28,2.65,1.35",
      "24548539,2,1.15,4.40,1.20,4.10",
      "24548539,9,1.118,5.50,1.182,4.40",
      "24548539,8,1.10,7.50,1.20,4.75"
    ],
    "total": [
      "22548537,4,155.5,0.76,0.88,155.5,0.76,0.88,155.5,0.76,0.88",
      "22548537,5,156,0.97,0.90,156,0.92,0.94,156,0.92,0.94",
      "22548537,6,156,0.861,0.899,156,0.899,0.861,156,0.899,0.861",
      "22548537,11,158.5,0.90,0.90,156,0.90,0.90,156,0.90,0.90",
      "22548537,12,158.5,0.85,0.833,156.5,0.875,0.825,156.5,0.875,0.825"
    ]
  }
}

 Match Stats

Update Time: 2026-04-22 11:02Change Log
Introduction

• This API endpoint returns instant technical statistics of basketball matches(GMT +0 0:00-23:59).
Default: technical statistics for matches within 24 hours

• Player statistics currently supports NBA、WNBA、CBA、Asociación de Clubes de Baloncesto、Basketball Bundesliga、Ligue Nationale de Basket、Lega Basket Serie A、Euro、Russian Basketball Super League、NBL(A)、Korea Basketball League、Basketball Japan League.

• By using endpoints Schedule & Results (Basic) and Match Modify Record, you can get basic information of matches.

• The following offensive statistics can be calculated using formulas.
- Free Throws Percentage (FT%) = Free Throws Made / Free Throws Attempts
- 2-Pointers Percentage (2P%) = 2-Pointers Field Goals Made / 2-Pointers Attempts
- 3-Pointers Percentage (3P%) = 3-Pointers Field Goals Made / 3-Pointers Attempts
- Field Goals Percentage (FG%) = Field Goals Made / Field Goals Attempts
- Total Rebounds (Reb) = Defensive Rebounds + Offensive Rebounds
Related Plans

You can use this api by subscribing plans:  Stats.
Request

    Path: /sport/basketball/stats
    Method: GET
    Calls: This interface is limited to 3 second/call;
    Recommend Calls: 10 second/call
    Parameters: 

Parameter	Value	Required	Description
date	string	false	yyyy-MM-dd, e.g. 2019-08-01.
It is limited to query the past week.
matchId	string	false	Search by match ID
Response

Parameter	Value	Description
matchId 	string	
homeTeamName 	string	
awayTeamName 	string	
costTime 	string	
homeScore 	int	
homeFastScore 	int	
homeInsideScore 	int	
homeLeadingScore 	int	
homeTotalMiss 	int	
awayScore 	int	
awayFastScore 	int	
awayInsideScore 	int	
awayLeadingScore 	int	
awayTotalMiss 	int	
homePlayers 	list	
	playerId 	string	
playerName 	string	
location 	string	There are positional data for the starting lineup, such as center, defender, etc.; there is no data for the substitute.
playingTime 	int	
shootHit 	int	
shoot 	int	
threePointHit 	int	
threePointShot 	int	
penaltyShotHit 	int	freeThrowHit
penaltyShot 	int	freeThrowShoot
attack 	int	offensiveRebound
defend 	int	defensiveRebound
assist 	int	
foul 	int	
rob 	int	steal
miss 	int	turnover
cover 	int	block
score 	int	
onFloor 	boolean	Is it on floor?
awayPlayers 	list	
	playerId 	string	
playerName 	string	
location 	string	There are positional data for the starting lineup, such as center, defender, etc.; there is no data for the substitute.
playingTime 	int	
shootHit 	int	
shoot 	int	
threePointHit 	int	
threePointShot 	int	
penaltyShotHit 	int	freeThrowHit
penaltyShot 	int	freeThrowShoot
attack 	int	offensiveRebound
defend 	int	defensiveRebound
assist 	int	
foul 	int	
rob 	int	steal
miss 	int	turnover
cover 	int	block
score 	int	
onFloor 	boolean	Is it on floor?
Example Request

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class SportDemo {
  public static void main(String[] args) {
    // Set url parameter
    String url = "http://api.isportsapi.com/sport/basketball/stats?api_key=<YOUR_API_KEY>";

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
http://api.isportsapi.com/sport/basketball/stats?api_key=<YOUR_API_KEY>

{

  "code": 0,

  "message": "success",

  "data": [
    {

      "matchId": "14022637",

      "homeTeamName": "Toronto Raptors",

      "awayTeamName": "Houston Rockets",

      "costTime": "136",

      "homeScore": 134,

      "homeFastScore": 28,

      "homeInsideScore": 64,

      "homeLeadingScore": 5,

      "homeTotalMiss": 25,

      "awayScore": 129,

      "awayFastScore": 11,

      "awayInsideScore": 50,

      "awayLeadingScore": 17,

      "awayTotalMiss": 20,

      "homePlayers": [
        {

          "playerId": "5283",

          "playerName": "OG Anunoby",

          "location": "F",

          "playingTime": 20,

          "shootHit": 3,

          "shoot": 5,

          "threePointHit": 1,

          "threePointShot": 1,

          "penaltyShotHit": 0,

          "penaltyShot": 0,

          "attack": 0,

          "defend": 3,

          "assist": 2,

          "foul": 2,

          "rob": 1,

          "miss": 3,

          "cover": 0,

          "score": 7,

          "onFloor": false
        
},

        {


      ]
    
}
  ]

}