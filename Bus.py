import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt

import pandas as pd
from pandas import DataFrame
from requests import get
from tqdm import tqdm


class Data:
    """Data is a data class of route information communicating others funciton"""
    data: DataFrame
    stop_list: DataFrame

    def __init__(self, debug: bool = False) -> None:
        """the parameter of debug will decide the source of route data"""
        if debug:
            self.data = self._load_data()               # access the csv file "bus_data.csv" 
        else:
            self.data = self._initial_master_data()     # start to scrap the NWFB, KMB, CTB bus data from Data.Gov.HK 
        pass

    def stops_search(self, location: tuple, eta: bool = False) -> DataFrame:
        
        """
        input   : the user current location sourced from telegram bot
        process : filter stops with specified effective distance regarding the location
        output  : the Data class storing all the route-stops information which are within the effective distance
        """

        result = self.data.copy()
        result["distance"] = result.location.apply(
            lambda row: self._calculate_distance(row, location)
        )
        condition = result.distance < Functions.EFFECTIVE_DISTANCE
        result = result[condition].sort_values(
            by="distance", ascending=True, inplace=False
        )
        result.drop_duplicates(
            subset=["co", "route", "dir", "service_type"], keep="first", inplace=True
        )
        result = result[condition]
        if eta: return self._load_eta(result)
        return result.drop(["location", "distance", "stop"], axis=1)

    def point2point_match(
        self, location_current: tuple, location_target: tuple, eta: bool
    ) -> DataFrame:
        """
        input   : the user current location and target location sourced from telegram bot
        process : from two results of stops_search function, match the route number and direction with inner method
        output  : the Data class stroring all the route-stops information which are available to reach target location from current location 
        """

        result = self.stops_search(location_current, eta).merge(
            self.stops_search(location_target),
            on=["co", "route", "dir", "service_type"],
            suffixes=["", "_target"],
        )

        keep_list = ["co", "route", "seq", "name", "seq_target", "name_target"]
        if eta:
            keep_list += ["dest", "1", "2", "3"]
        return result[result.seq.astype("int") < result.seq_target.astype("int")][
            keep_list
        ].drop_duplicates(keep="first")

    def _load_stop_list(self, location: tuple) -> list:
        pass

    def _load_eta(self, bus_data: DataFrame) -> DataFrame:
        """
        input  : the Data class storing all the route-stops information
        process: From the Data.Gov.HK, scrap all the eta data regarding the route, then insert the eta_columns [{3 columns of eta}, destination]
        output : the Data class storing all the route-stops informtion with the eta_columns
        """

        eta_link = (
            bus_data[["co", "stop"]]
            .drop_duplicates(keep="first")
            .apply(lambda x: Company.generate_eta_url(x.co, x.stop), axis=1)
            .to_list()
        )

        bus_data = bus_data.merge(
            Spider(eta_link, Functions.ETA_STOP).execute(),
            how="inner",
            on=["co", "route", "dir", "seq", "service_type"],
        )

        data_columns = ["co", "route", "dir", "seq", "service_type", "dest", "name"]

        bus_info = bus_data[data_columns].copy().drop_duplicates(keep="first")
        for row in bus_data.itertuples():
            data_row = bus_info[
                (bus_info.co == row.co)
                & (bus_info.route == row.route)
                & (bus_info.dir == row.dir)
                & (bus_info.service_type == row.service_type)
                & (bus_info.dest == row.dest)
            ].index
            bus_info.loc[data_row, row.eta_seq] = row.eta[11:-9]
        return bus_info.drop_duplicates(
            keep="first", subset=["route", "dest", "1", "2", "3"]
        )

    def _initial_master_data(self) -> DataFrame:
        """
        process  :
            1) generate the route, stops, and route-stops url links for webscrapping in Data.Gov.HK
            2) data cleansing for storing as offline data
            3) save the route-stop to offline file
        
        output  : the Data class which contains all the route-stop information provided by NWFB, CTB and KMB
        """
        route = Spider(list(Company.route_url()), Functions.ROUTE).execute()
        route_stop_list = route.apply(
            lambda x: Company.generate_url(
                x.co, Functions.ROUTE_STOP, [x.co, x.route, "inbound"]
            ),
            axis=1,
        ).tolist()
        route_stop_list += route.apply(
            lambda x: Company.generate_url(
                x.co, Functions.ROUTE_STOP, [x.co, x.route, "outbound"]
            ),
            axis=1,
        ).tolist()
        route_stop = Spider(route_stop_list, Functions.ROUTE_STOP).execute()

        stop = []
        for row in (
            route_stop[["co", "stop"]].drop_duplicates(keep="first").itertuples()
        ):
            stop.append(Company.generate_url(row.co, Functions.STOP, [row.stop]))
        stop = Spider(stop, Functions.STOP).execute()
        data = route_stop.merge(stop, on="stop", how="inner")
        kmb_data = (
            Spider(
                [Company.generate_url("KMB", Functions.ROUTE_STOP)],
                Functions.ROUTE_STOP,
            )
            .execute()
            .merge(
                Spider(
                    [Company.generate_url("KMB", Functions.STOP)], Functions.STOP
                ).execute()
            )
        )
        data = data.append(kmb_data)
        return data.reset_index()

    def _load_data(self) -> DataFrame:
        data = pd.read_csv("bus_data.csv", dtype="string")
        data.drop("Unnamed: 0", axis=1, inplace=True)
        return data

    def _calculate_distance(self, x, y) -> float:
        """calculate the strict line distance of two points of locations """
        x = x.split(",")
        return sqrt(
            pow(float(y[0]) - float(x[0]), 2) + pow(float(y[1]) - float(x[1]), 2)
        )


class Spider:
    """this is a scrapping spider for scrapping the data from the Data.Gov.HK"""
    workers: ThreadPoolExecutor
    data: DataFrame

    def __init__(self, task: list, function: str) -> None:
        self.executor = ThreadPoolExecutor(max_workers=min(10, len(task)))      # decide how many workers involve to the task
        self.data = pd.DataFrame()                                              # final output
        self.task = task                                                        
        self.function = function                                                # the parameter of control flow decides which data cleansing action will be performed 
        pass

    def execute(self) -> None:
        list(
            tqdm(
                self.executor.map(self.action, self.task),
                total=len(self.task),
                leave=False,
            )
        )
        return self.data

    def store_data(self, raw) -> None:
        """receive the raw data and call the data cleansing action then insert the result to self.data"""
        self.data = self.data.append(self._refine_df(raw))

    def action(self, url) -> None:
        """the main of spider is responsible for requesting url, and return the json data"""
        while True:
            try:
                connection = get(url)
                if (connection.status_code == 200) & bool(
                    raw := connection.json().get("data")
                ):
                    if type(raw) is not list:
                        raw = [raw]
                    time.sleep(0.5)
                break
            except ConnectionResetError:
                time.sleep(5)
            except ConnectionAbortedError:
                time.sleep(5)
            except ConnectionError:
                time.sleep(5)
            except ConnectionRefusedError:
                time.sleep(5)

        if raw:
            self.store_data(pd.DataFrame(raw))

    def _refine_df(self, raw) -> DataFrame:
        """control flow of data cleansing action"""
        if self.function == Functions.ROUTE:
            return self._refine_route(raw)
        elif self.function == Functions.STOP:
            return self._refine_stops(raw)
        elif self.function == Functions.ROUTE_STOP:
            return self._refine_route_stop(raw)
        elif self.function == "eta_route":
            return self._refine_eta_route(raw)
        elif self.function == Functions.ETA_STOP:
            return self._refine_eta_stops(raw)

    def _refine_route(self, raw) -> DataFrame:
        raw.rename({"dest_tc": "dest"}, inplace=True, axis=1)
        return raw[["co", "route"]]

    def _refine_stops(self, raw) -> DataFrame:
        raw["location"] = raw.apply(lambda x: ",".join([x.lat, x.long]), axis=1)
        raw.rename({"name_tc": "name"}, inplace=True, axis=1)
        raw.name = raw.name.apply(lambda x: x.split(", ")[0] if "," in x else x)
        return raw[["stop", "name", "location"]]

    def _refine_route_stop(self, raw) -> None:
        raw.rename({"bound": "dir"}, inplace=True, axis=1)
        if "data_timestamp" in raw.columns:
            raw.drop("data_timestamp", axis=1, inplace=True)
        if "co" not in raw.columns:
            raw["co"] = pd.Series()
            raw.co.fillna("KMB", inplace=True)
        if "service_type" not in raw.columns:
            raw["service_type"] = pd.Series(dtype="string")
            raw.service_type.fillna("0", inplace=True)
        return raw

    def _refine_eta_route(self, raw) -> None:
        pass

    def _refine_eta_stops(self, raw) -> None:
        info_col = [
            "co",
            "route",
            "dir",
            "seq",
            "dest",
            "service_type",
            "eta",
            "eta_seq",
        ]
        raw.sort_values(by=["route", "eta_seq"], inplace=True)
        raw.rename({"dest_tc": "dest"}, inplace=1, axis=1)
        raw.dropna(subset=["eta"], inplace=True)

        info = {}
        for col in info_col:
            info[col] = []
        for row in raw.itertuples():
            for col in info:
                if col in raw.columns:
                    info[col].append(row[row._fields.index(col)])
                else:
                    if col == "service_type":
                        info[col].append("0")
                    if col == "co":
                        info[col].append("KMB")
        eta = pd.DataFrame(info, dtype="string")
        eta["mins"] = eta.eta.map(
            lambda clock: abs(
                datetime.strptime(clock[:-9], "%Y-%m-%dT%H:%M") - datetime.now()
            ).seconds
            // 60
            if clock
            else "",
            na_action="ignore",
        )
        return eta.fillna(" ")


class Company:
    """it is a data class which is responsible for generating the url with parameters for the Spider"""
    KMB = "KMB"
    NWFB = "NWFB"
    CTB = "CTB"
    url_reference = {
        "KMB": "https://data.etabus.gov.hk/v1/transport/kmb",
        "CTB": "https://rt.data.gov.hk/v1/transport/citybus-nwfb",
        "NWFB": "https://rt.data.gov.hk/v1/transport/citybus-nwfb",
    }

    def generate_url(co: str, function: str, parameter: list = None) -> str:
        prefix = Company.url_reference.get(co)
        if parameter and type(parameter) is not list:
            parameter = [parameter]  # reform the list type
        parameter = "/".join(parameter) if parameter else ""
        return "/".join([prefix, function, parameter])

    def route_url() -> list:
        for co in [Company.NWFB, Company.CTB]:
            yield Company.generate_url(co, Functions.ROUTE, [co])

    def generate_eta_url(co: str, stop_code: str) -> str:
        stops_url = {
            "KMB": f"https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/stop_code",
            "CTB": f"https://rt.data.gov.hk/v1/transport/batch/stop-eta/ctb/stop_code?lang=zh-hant",
            "NWFB": f"https://rt.data.gov.hk/v1/transport/batch/stop-eta/nwfb/stop_code?lang=zh-hant",
        }
        return stops_url.get(co).replace("stop_code", stop_code)


class Functions:
    STOP = "stop"
    ROUTE_STOP = "route-stop"
    ROUTE = "route"
    EFFECTIVE_DISTANCE = 0.007
    ETA_STOP = "eta_stop"


if __name__ == "__main__":
    debug = True
    MASTER = Data(debug)
    if ~debug:
        MASTER.data.to_csv("bus_data.csv")
    CURRENT = (22.3276524, 114.1660167)
    TARGET = (22.2946943, 114.1688353)
    result = MASTER.point2point_match(TARGET, CURRENT, True)
    result = MASTER.stops_search(CURRENT, True)
    print(result)
