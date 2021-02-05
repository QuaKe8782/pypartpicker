import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class Part:

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.url = kwargs.get("url")
        self.type = kwargs.get("type")
        self.price = kwargs.get("price")
        self.image = kwargs.get("image")


class PCPPList:

    def __init__(self, **kwargs):
        self.parts = kwargs.get("parts")
        self.wattage = kwargs.get("wattage")
        self.total = kwargs.get("total")
        self.url = kwargs.get("url")
        self.compatibility = kwargs.get("compatibility")

class Product(Part):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.specs = kwargs.get("specs")
        self.price_list = kwargs.get("price_list")
        self.rating = kwargs.get("rating")
        self.reviews = kwargs.get("reviews")
        self.compatible_parts = kwargs.get("compatible_parts")

class Price:

    def __init__(self, **kwargs):
        self.value = kwargs.get("value")
        self.seller = kwargs.get("seller")
        self.seller_icon = kwargs.get("seller_icon")
        self.url = kwargs.get("url")
        self.base_value = kwargs.get("base_value")
        self.in_stock = kwargs.get("in_stock")

class Review:

    def __init__(self, **kwargs):
        self.author = kwargs.get("author")
        self.author_url = kwargs.get("author_url")
        self.author_icon = kwargs.get("author_icon")
        self.points = kwargs.get("points")
        self.created_at = kwargs.get("created_at")
        self.rating = kwargs.get("rating")
        self.content = kwargs.get("content")

def make_soup(url) -> BeautifulSoup:
    # sends a request to the URL
    page = requests.get(url)
    # gets the HTML code for the website and parses it using Python's built in HTML parser
    soup = BeautifulSoup(page.content, 'html.parser')
    # returns the HTML
    return soup


def fetch_list(list_url) -> PCPPList:

    # checks if its a pcpartpicker list and raises an exception if its not or if the list is empty
    if not "pcpartpicker.com/list/" in list_url or list_url.endswith("/list/"):
        raise Exception(f"'{list_url}' is an invalid PCPartPicker list!")

    # fetches the HTML code for the website
    try:
        soup = make_soup(list_url)
    except requests.exceptions.ConnectionError:
        raise ValueError("Invalid list URL! Max retries exceeded with URL.")


    # gets the code with the table containing all the parts
    table = soup.find_all("table", {"class": "xs-col-12"}, limit=1)[0]

    # creates an empty list to put the Part objects inside
    parts = []

    # iterates through every part in the table
    for item in table.find_all('tr', class_="tr__product"):
        # creates a new part object using values obtained from the tables' rows
        part_object = Part(
            name = item.find(class_="td__name").get_text().strip('\n'),
            price = item.find(class_="td__price").get_text().strip('\n').replace("No Prices Available", "None").replace("Price", "").strip('\n'),
            type = item.find(class_="td__component").get_text().strip('\n').strip(),
            image = ("https://" + item.find("img", class_="")["src"]).replace("https://https://", "https://")
        )
        # converts string representation of 'None' to NoneType
        if part_object.price == 'None':
            part_object.price = None
        # checks if the product row has a product URL inside
        if 'href' in str(item.find(class_="td__name")):
            # adds the product URL to the Part object
            part_object.url = "https://" + urlparse(list_url).netloc + item.find(class_="td__name").find("a")["href"].replace("/placeholder-", "")
        # adds the part object to the list
        parts.append(part_object)

    # gets the estimated wattage for the list
    wattage = soup.find(class_="partlist__keyMetric").get_text().replace("Estimated Wattage:", "").strip('\n')

    # gets the total cost for the list
    total_cost = table.find("tr", class_="tr__total tr__total--final").find(class_="td__price").get_text()

    # gets the compatibility notes for the list
    compatibilitynotes = [a.get_text().strip('\n').replace("Note:", "").replace("Warning!", "") for a in soup.find_all("li", class_=["info-message", "warning-message"])]

    # returns a PCPPList object containing all the information
    return PCPPList(parts=parts, wattage=wattage, total=total_cost, url=list_url, compatibility=compatibilitynotes)



def fetch_product(part_url) -> Product:

    if not "pcpartpicker.com" in part_url and "/product/" in part_url:
        raise ValueError("Invalid product URL!")

    try:
        soup = make_soup(part_url)
    except requests.exceptions.ConnectionError:
        raise ValueError("Invalid product URL! Max retries exceeded with URL.")


    specs_block = soup.find(class_="block xs-hide md-block specs")

    specs = {}
    prices = []
    price = None

    table = soup.find("table", class_="xs-col-12")
    section = table.find("tbody")

    for row in section.find_all("tr"):
        if "tr--noBorder" in str(row):
            continue
        price_object = Price(
            value = row.find(class_="td__finalPrice").get_text().strip('\n'),
            seller = row.find(class_="td__logo").find("img")["alt"],
            seller_icon = ("https://" + row.find(class_="td__logo").find("img")["src"][1:]).replace("https://https://", "https://"),
            base_value = row.find(class_="td__base priority--2").get_text(),
            url = "https://" + urlparse(part_url).netloc + row.find(class_="td__finalPrice").find("a")["href"],
            in_stock = True if "In stock" in row.find(class_="td__availability").get_text() else False
        )
        if price is None and "In stock" in row.find(class_="td__availability").get_text():
            price = price_object
        prices.append(price_object)

    for spec in specs_block.find_all("div", class_="group group--spec"):
        specs[spec.find("h3", class_="group__title").get_text()] = spec.find("div", class_="group__content").get_text().strip().strip('\n').replace("\u00b3", '').replace('\"', '').split('\n')

    reviews = None

    review_box = soup.find(class_="block partReviews")

    if review_box != None:

        reviews = []

        for review in review_box.find_all(class_="partReviews__review"):
            stars = 0
            for star in review.find(class_="product--rating list-unstyled").find_all("li"):
                if ' '.join(star.find("svg")["class"]) == "icon shape-star-full":
                    stars += 1

            iterations = 0
            for info in review.find(class_="userDetails__userData list-unstyled").find_all("li"):
                if iterations == 0:
                    points = info.get_text().replace(" points", '').replace(" point", '')
                elif iterations == 1:
                    created_at = info.get_text().replace(" ago", '')
                else:
                    break
                iterations += 1



            review_object = Review(
                author = review.find(class_="userDetails__userName").get_text(),
                author_url = "https://" + urlparse(part_url).netloc + review.find(class_="userDetails__userName")["href"],
                author_icon = "https://" + urlparse(part_url).netloc + review.find(class_="userAvatar userAvatar--entry").find("img")["src"],
                content = review.find(class_="partReviews__writeup markdown").get_text(),
                rating = stars,
                points = points,
                created_at = created_at
            )

            reviews.append(review_object)

    compatible_parts = None
    compatible_parts_list = soup.find(class_="compatibleParts__list list-unstyled")
    if compatible_parts_list != None:
        compatible_parts = []
        for item in compatible_parts_list.find_all("li"):
            compatible_parts.append((
                item.find("a").get_text(), "https://" + urlparse(part_url).netloc + item.find("a")["href"]
            ))

    product_object = Product(
        name = soup.find(class_="pageTitle").get_text(),
        url = part_url,
        image = None,
        specs = specs,
        price_list = prices,
        price = price,
        rating = soup.find(class_="actionBox actionBox__ratings").find(class_="product--rating list-unstyled").get_text().strip('\n').strip().strip("()"),
        reviews = reviews,
        compatible_parts = compatible_parts,
        type = soup.find(class_="breadcrumb").find(class_="list-unstyled").find("li").get_text()
    )

    image_box = soup.find(class_="single_image_gallery_box")

    if image_box != None:
        product_object.image = image_box.find("img")["src"].replace("https://https://", "https://")

    return product_object



def product_search(search_term, **kwargs) -> Part:

    search_term = search_term.replace(' ', '+')

    # makes sure limit is an integer, raises ValueError if it's not
    if not isinstance(kwargs.get("limit", 20), int):
        raise ValueError("Product limit must be an integer!")

    # checks if the region given is a string, and checks if it is a country code
    if not isinstance(kwargs.get("region", "us"), str) or len(kwargs.get("region", "us")) != 2:
        raise ValueError("Invalid region!")

    # constructs the search URL
    if kwargs.get("region") in ("us", None):
        search_link = f"https://pcpartpicker.com/search/?q={search_term}"
    else:
        search_link = f"https://{kwargs.get('region', '')}.pcpartpicker.com/search/?q={search_term}"

    try:
        # fetches the HTML code for the website
        soup = make_soup(search_link)
    except requests.exceptions.ConnectionError:
        # raises an exception if the region is invalid
        raise ValueError("Invalid region! Max retries exceeded with URL.")

    # checks if the page redirects to a product page
    if soup.find(class_="pageTitle").get_text() != "Product Search":

        # creates a part object with the information from the product page
        part_object = Part(
            name = soup.find(class_="pageTitle").get_text(),
            url = search_link,
            price = None
        )

        # searches for the pricing table
        table = soup.find("table", class_="xs-col-12")

        # loops through every row in the table
        for row in table.find_all("tr"):

            # first conditional statement makes sure its not the top row with the table parameters, second checks if the product is out of stock
            if not "td__availability" in str(row) or "Out of stock" in row.find(class_="td__availability").get_text():

                # skips this iteration
                continue

            # sets the price of the price object to the price
            part_object.price = row.find(class_="td__finalPrice").get_text().strip('\n').strip("+")

            # ends the loop
            break

        # returns the part object
        return [part_object]

    # gets the section of the website's code with the search results
    section = soup.find("section", class_="search-results__pageContent")

    # creates an empty list for the part objects to be stored in
    parts = []

    # iterates through all the HTML elements that match the given the criteria
    for product in section.find_all("ul", class_="list-unstyled"):
        # extracts the product data from the HTML code and creates a part object with that information
        part_object = Part(
            name = product.find("p", class_="search_results--link").get_text().strip(),
            url = product.find("p", class_="search_results--link").find("a", href=True)["href"],
            image = ("https://" + product.find("img")["src"].strip('/')).replace("https://https://", "https://")
        )
        try:
            part_object.price = product.find(class_="product__link product__link--price").get_text()
        except AttributeError:
            part_object.price = None

        # adds the part object to the list
        parts.append(part_object)

    # returns the part objects
    return parts[:kwargs.get("limit", 20)]