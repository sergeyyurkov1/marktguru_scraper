import time
import warnings

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import pandas as pd
from openpyxl import load_workbook
from datetime import date


def set_location(driver, first_item: str, zip: str):
    try:
        driver.get(
            f"https://www.marktguru.de/search/{first_item}?title={first_item}&page=0"
        )

        time.sleep(15)  # Waits for the page to load

        # Tries to remove view-locking elements
        e = driver.find_element(By.ID, "usercentrics-root")
        driver.execute_script("arguments[0].remove();", e)

        # Opens location input
        driver.find_element(By.CLASS_NAME, "location-default-text").click()

        time.sleep(5)

        # Selects the location input and enters the ZIP code
        inputs = driver.find_elements(By.TAG_NAME, "input")
        inputs[1].send_keys(zip + Keys.ENTER)

        time.sleep(5)

        # Selects the first address
        driver.switch_to.active_element.send_keys(Keys.ARROW_DOWN)
        time.sleep(2)
        driver.switch_to.active_element.send_keys(Keys.ENTER)

        time.sleep(5)

        return True
    except Exception as e:
        print()
        print(e)
        print()
        print("The page didn't load right. Please restart.")
        print()

        return False


def search_page(driver, url: str, item: str, page: int, zip_: str) -> list:
    results = []

    driver.get(f"{url}/{item}?title={item}&page={page}")

    driver.get(driver.current_url)

    driver.implicitly_wait(10)

    # Exit condition: last page found, continues with the next item
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "headline"))
    )
    assert item.upper() in driver.find_element(By.CLASS_NAME, "headline").text

    # Waits until the Item cards are loaded - affects the results
    WebDriverWait(driver, 120).until(
        EC.visibility_of_all_elements_located((By.TAG_NAME, "li"))
    )

    if zip_ not in driver.find_element(By.CLASS_NAME, "location-text").text:
        print()
        print("Location error!")
        print()

    # Parses the page
    bs = BeautifulSoup(driver.page_source, "html.parser")

    for li in bs.select("li"):

        h3 = li.select("h3")

        i = {}

        if len(h3) > 0:
            i["Item"] = item

            i["Name"] = "".join([x.text for x in h3]).rstrip().lower()

            dd = li.select("dl > dt.dates + dd")
            i["Date valid"] = "".join([x.text for x in dd]).rstrip().lower()

            a = li.select("dl > dt.retailer + dd > a")
            if len(list(a)) == 0:
                span = li.select("dl > dt.retailer + dd > span")
                i["Store"] = "".join([x.text for x in span]).rstrip().lower()
            else:
                i["Store"] = "".join([x.text for x in a]).rstrip().lower()

            brand_a = li.select("dl > dt.brand + dd > a")
            if len(list(brand_a)) == 0:
                brand_span = li.select("dl > dt.brand + dd > span")
                i["Brand"] = "".join([x.text for x in brand_span]).rstrip().lower()
            else:
                i["Brand"] = "".join([x.text for x in brand_a]).rstrip().lower()

            price_strong = li.select("p > strong")
            if len(list(price_strong)) == 0:
                price_dd = li.select("dl > div.prices-container> dt.price + dd")
                price_p = li.select("p")

                i["Price"] = "".join([x.text for x in price_dd]).rstrip().lower()
                i["Note"] = "".join([x.text for x in price_p]).rstrip().lower()
            else:
                i["Price"] = (
                    "".join([x.text for x in price_strong])
                    .split("-")[0]
                    .rstrip()
                    .lower()
                )

            # print(i)

            results.append(i)
        else:
            continue

    return results


def launch_scraper(driver, url, moe, shopping_list, zip_):
    data = []

    for item in shopping_list:
        print()
        print("  ", f"Searching for '{item}'")
        print()

        page = 0
        while True:
            print("   ", f"Page {page + 1}")
            try:
                page_results = search_page(driver, url, item, page, zip_)
                empty_results = 0
                for result in page_results:
                    if (
                        result["Name"] == ""
                        or result["Price"] == ""
                        or result["Store"] == ""
                    ):
                        empty_results += 1
                if empty_results > moe:
                    raise ValueError(
                        f"Got more than {moe} empty result(s). Retrying..."
                    )  # see the config file

                data.extend(page_results)
            except ValueError as e:
                print("    ", e)
                page -= 1
            except AssertionError:
                print()
                print("    ", "Reached the last page.")
                break
            except Exception as e:
                print(e)

            page += 1

    return data


def generate_output(data, lp, item_blacklist) -> str:
    warnings.simplefilter(action="ignore", category=FutureWarning)

    df = pd.DataFrame(data)

    # Removing empty rows because of possible scraping errors
    df = df[(df["Name"] != "") & (df["Store"] != "") & (df["Price"] != "")]
    # Removing duplicate entries because of possible scraping errors
    df.drop_duplicates(subset=["Name", "Price", "Date valid"], keep=False, inplace=True)

    df = df[~df["Name"].isin(item_blacklist)]

    # Handles Price and Units
    df[["Price", "Unit"]] = df["Price"].str.split("/", expand=True)

    def str_to_float(x: str) -> float:
        try:
            return float(x.split(" ")[1].replace(",", "."))
        except ValueError:
            return 999.9  # returns 999.9 if cannot process the price

    df["Price"] = df["Price"].apply(lambda x: str_to_float(x))
    df.sort_values(
        ["Store", "Item", "Price"], ascending=True, inplace=True
    )  # sorting the Price from lowest to highest

    # Reordering columns
    try:
        df = df[
            ["Store", "Item", "Name", "Brand", "Price", "Unit", "Date valid", "Note"]
        ]
    except KeyError:
        df = df[["Store", "Item", "Name", "Brand", "Price", "Unit", "Date valid"]]

    # Lastly: Lowest price indicator
    df["LP"] = df.groupby([lp])["Price"].transform("min")
    df["Lowest price across stores"] = df.apply(
        lambda x: f"✅ {x[lp]}" if x["LP"] == x["Price"] else "", axis=1
    )
    df.drop(["LP"], axis=1, inplace=True)  # remove the temporary column

    # Handles the output
    # ------------------------------------------------------
    today = date.today()

    gbo = df.groupby(["Store"])

    # Creates an empty Excel file
    blank_line = pd.DataFrame()
    blank_line.to_excel(f"{today}.xlsx", index=False)

    # Loads the file, sets up the Excel Writer
    book = load_workbook(f"{today}.xlsx")
    writer = pd.ExcelWriter(f"{today}.xlsx", engine="openpyxl")
    writer.sheets.update({ws.title: ws for ws in book.worksheets})

    # Writes result tables to the file
    for e, (_, o) in enumerate(gbo):
        o[["Store", "Item"]] = o[["Store", "Item"]].where(
            o[["Store", "Item"]].apply(lambda x: x != x.shift()), ""
        )
        if e == 0:
            o.to_excel(writer, index=False)
        else:
            o.to_excel(
                writer, startrow=writer.sheets["Sheet1"].max_row + 1, index=False
            )

    writer.close()

    return f"{today}.xlsx"
