from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd
import time
import random
from selenium.webdriver.edge.options import Options
import os
from bs4 import BeautifulSoup


def slow_smooth_scroll(driver, total_scroll_time=15):
    """Perform slow and smooth scrolling on a page."""
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    start_time = time.time()
    current_position = 0

    while time.time() - start_time < total_scroll_time:
        # Calculate a smooth, smaller random scroll step
        scroll_step = random.randint(50, 200)

        # Randomly decide to scroll down or slightly up for natural behavior
        if random.random() < 0.85:  # 85% chance to scroll down
            current_position += scroll_step
        else:
            current_position -= random.randint(30, 100)  # Small upward scroll

        # Ensure the position stays within the page bounds
        current_position = max(0, min(current_position, scroll_height - viewport_height))
        
        # Execute the scroll
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        
        # Pause slightly longer for smooth, slower behavior
        time.sleep(random.uniform(0.2, 0.5))  # Moderate, varying delays

    # Scroll back up slightly at the end for realism
    driver.execute_script(f"window.scrollTo(0, {max(0, current_position - 300)});")



def simulate_mouse_movement(driver):
    """Simulate mouse movement to mimic human interactions."""
    try:
        actions = ActionChains(driver)
        element = driver.find_element(By.TAG_NAME, "body")
        actions.move_to_element(element)
        for _ in range(random.randint(5, 15)):
            x_offset = random.randint(-10, 10)
            y_offset = random.randint(-10, 10)
            actions.move_by_offset(x_offset, y_offset).perform()
            time.sleep(random.uniform(0.1, 0.5))
    except Exception as e:
        print(f"Mouse movement simulation failed: {e}")


def close_popup(driver):
    """Check for and close the popup button if it exists."""
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.exit-popup__close"))
        )
        close_button = driver.find_element(By.CSS_SELECTOR, "button.exit-popup__close")
        ActionChains(driver).move_to_element(close_button).click(close_button).perform()
        print("Popup closed.")
    except Exception:
        pass

def scrape_data(brands, start_page, end_page):      # Configure Edge options
    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--disable-gpu")  
    options.add_argument("--no-sandbox") 
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--incognito")

    # Add desired capabilities using options
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Randomize user-agent
    user_agent = random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0"
    ])
    options.add_argument(f"user-agent={user_agent}")

    # Initialize the WebDriver
    driver = webdriver.Edge(options=options)

    scraped_data = []

    for brand_url in brands:
        page = 1
        product_links = []
        
        for page in range(start_page, end_page + 1):
            print(f"Scraping page {page} of {brand_url}")
            driver.get(f"{brand_url}?page={page}")
        
            # Human-like interaction
            time.sleep(random.uniform(2, 5))
            close_popup(driver)
            time.sleep(2)
            slow_smooth_scroll(driver, total_scroll_time=5)  # Scroll for 5 seconds
            simulate_mouse_movement(driver)
            
            try:
                products = driver.find_elements(By.CSS_SELECTOR, "a.product-item__image-wrapper")
                if not products:
                    print(f"No products found on page {page}. Ending scrape.")
                    break
        
                for product in products:
                    href = product.get_attribute("href")
                    product_links.append(href)
        
                print(f"Scraped {len(products)} products from page {page}.")
            except Exception as e:
                print(f"Error collecting product links on page {page}: {e}")
                break

        print(f"Found {len(product_links)} products on {brand_url}.")

        count = 1
        for product_url in product_links:
            print(product_url)
            try:
                driver.get(product_url)
                time.sleep(3)

                driver.execute_script("window.scrollBy(0, 100)")

                title = driver.find_element(By.CSS_SELECTOR, "h1.product-meta__title.heading.h1").text.strip()

                # Extract handle from the URL
                handle = product_url.split('/')[-1].split('?')[0]

                # Locate all variations
                variations = driver.find_elements(By.CSS_SELECTOR, ".variant-swatch__radio")[::-1]
                num_variations = len(variations)

                # Get all images
                image_elements = driver.find_elements(By.CSS_SELECTOR, ".product-gallery__thumbnail img")
                all_image_src = [img.get_attribute("src") for img in image_elements]

                # Filtered images (non-variation images)
                filtered_images = all_image_src[:len(all_image_src) - num_variations]
                variation_images = all_image_src[-num_variations:][::-1]  # Reverse variation images

                # Breadcrumb type
                breadcrumb_type = ""
                try:
                    breadcrumb_type = driver.find_element(
                        By.CSS_SELECTOR, "li.breadcrumb__item a[href*='types']"
                    ).text.strip()
                except:
                    pass

                # Vendor
                vendor = driver.find_element(By.CSS_SELECTOR, "a.product-meta__vendor").text.strip()

                # Option 1 (e.g., Size)
                option1_value = driver.find_element(By.CSS_SELECTOR, "span.block-swatch__item-text").text.strip()

                # SEO description
                product_description_box = ""
                try:
                    seo_description_element = driver.find_element(By.CSS_SELECTOR, "div.rte.text--pull > p")
                    product_description_box = seo_description_element.text.strip()
                except:
                    pass

                # Applications and usage tags
                application = ""
                usage = ""
                try:
                    application = driver.find_element(By.XPATH, "//tr[th[contains(text(), 'Application:')]]").text.strip()
                    application = application.split(':', 1)[1].strip()
                except:
                    pass

                try:
                    usage = driver.find_element(By.XPATH, "//tr[th[contains(text(), 'Usage:')]]").text.strip()
                    usage = usage.split(':', 1)[1].strip()
                except:
                    pass

                tags = application + usage
                tags = tags.replace(" | ", ", ")
                # Surface type attribute
                surface_attribute = ""
                try:
                    surface_type = driver.find_element(By.XPATH, "//tr[th[contains(text(), 'Surface Type:')]]").text.strip()
                    surface_attribute = surface_type.split(':', 1)[1].strip()
                except:
                    pass

                # Loop through variations
                image_positions = list(range(1, len(filtered_images) + 1))

                length_of_variations = len(variations)
                for idx, variation in enumerate(variations):
                    label = driver.find_element(By.CSS_SELECTOR, f"label[for='{variation.get_attribute('id')}']")

                    # Scroll to the label and click it
                    ActionChains(driver).move_to_element(label).perform()
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(label)).click()
                    time.sleep(2)  # Allow page to update

                    # Extract variation-specific details
                    current_url = driver.current_url
                    variant_id = current_url.split("variant=")[-1]

                    variation_name = variation.get_attribute("value")
                    option2_value = driver.find_element(By.CSS_SELECTOR, "span.product-form__selected-value").text.strip()
                    variant_sku = driver.find_element(By.CSS_SELECTOR, "span.product-meta__sku-number").text.strip()

                    # Find all price elements
                    price_elements = driver.find_elements(By.CSS_SELECTOR, "span.box-price-pcsPerCarton")

                    # Extract correct price based on variant_id
                    if length_of_variations>1:
                        for price_element in price_elements:
                            if price_element.get_attribute("data-id") == variant_id:
                                variant_price = price_element.get_attribute("data-price")
                                variant_compare_price = price_element.get_attribute("data-compare-price")
                                break  
                    else:
                        variant_price = driver.find_element(By.CSS_SELECTOR, "span.box-price-pcsPerCarton").get_attribute("data-price")
                        variant_compare_price = driver.find_element(By.CSS_SELECTOR, "span.box-price-pcsPerCarton").get_attribute("data-compare-price")


                    price_per_sq_ft_text = ""
                    try:
                        price_per_sq_ft_element = driver.find_element(By.CSS_SELECTOR, "span.price.price--highlight")
                        price_per_sq_ft_text = price_per_sq_ft_element.text.strip().replace("Sale price", "").strip()
                    except Exception as e:
                        print(f"Price Per Sq Ft Error: {e}")

                
                    original_price = ""
                    try:
                        original_price_text = driver.find_element(By.CSS_SELECTOR, "span.price.price--compare").text.strip()
                        original_price = original_price_text.replace("Regular price", "").strip()
                    except:
                        pass

                   
                    if length_of_variations > 1:
                        variant_barcode = ""
                        try:
                            variant_barcode = driver.find_element(By.CSS_SELECTOR, "tr.table-row-spec.barcode-container.d-none").get_attribute("data-value")
                        except:
                            pass
                    else:
                        variant_barcode = ""
                        try:
                            barcode_element = driver.find_element(By.CSS_SELECTOR, "tr.table-row-spec.barcode-container")
                            variant_barcode = barcode_element.get_attribute("data-value")
                        except:
                            pass

                    weight = ""
                    try:
                        weight_container = driver.find_element(By.XPATH, "//tr[th[contains(text(), 'Weight:')]]")
                        weight = weight_container.find_element(By.CSS_SELECTOR, "td.spec-values").text.strip()
                    except:
                        pass

                    uom = row_html = driver.find_element(By.XPATH, f"//tr[th[contains(text(), 'UOM:')]]").get_attribute("outerHTML")
                    # get the text from uom
                    uom = uom.split('<td class="spec-values">')[1].split('</td>')[0]
                    


                    # Find all <tr> tags with the matching data-id
                    rows = driver.find_elements(By.CSS_SELECTOR, f"tr[data-id='{variant_id}']")
                    tr_tags_html = [row.get_attribute("outerHTML") for row in rows]

                    # Initialize the relevant table HTML
                    relevant_table_html = "<table>"

                    # Add the <tr> tags matching the data-id to relevant_table_html
                    for tr_tag in tr_tags_html:
                        relevant_table_html += tr_tag

                    # Collect additional fields by matching specific table headers
                    if length_of_variations>1:
                        fields_to_append = [
                                        "Weight", "Width","UOM","Length", "Thickness", "Collection", "Composition",
                                        "Design", "Ends", "Edges", "Surface Type", "Installation Type",
                                        "Usage", "Application"
                                    ]
                        
                    else:
                        fields_to_append = [
                                        "PCs per box","Coverage Area","Color Shade","Weight", "Width","UOM","Length", "Thickness", "Collection", "Composition",
                                        "Design", "Ends", "Edges", "Surface Type", "Installation Type",
                                        "Usage", "Application"
                                    ]

                    for field in fields_to_append:
                        try:
                            # Locate the <tr> row with the specific field header and add its outerHTML
                            row_html = driver.find_element(By.XPATH, f"//tr[th[contains(text(), '{field}:')]]").get_attribute("outerHTML")
                            relevant_table_html += row_html
                        except Exception as e:
                            # Skip if the field is not found
                            print(f"Field '{field}' not found. Skipping. Error: {e}")

                    # Close the table HTML
                    relevant_table_html += "</table>"


                    
                    seo_description_element = driver.find_element(By.CSS_SELECTOR, "div.rte.text--pull > p")
                    variant_description = seo_description_element.text.strip()


                    soup = BeautifulSoup(relevant_table_html, "html.parser")

                    # Extract Coverage Area from <tr> where <th> contains 'Coverage Area'
                    coverage_area = ""
                    try:
                        coverage_area_element = soup.find("tr", class_="coverage-area-container")
                        if coverage_area_element:
                            coverage_area = coverage_area_element["data-value"].strip()
                    except:
                        pass

                    # Extract PCs per Box from <tr> where <th> contains 'PCs per Box'
                    pcs_per_box = ""
                    try:
                        pcs_per_box_element = soup.find("tr", class_="pcsPerBox-container")
                        if pcs_per_box_element:
                            pcs_per_box = pcs_per_box_element["data-value"].strip()
                    except:
                        pass

                    selected_image_url = ""
                    if length_of_variations>1:
                        try:
                            selected_image_element = driver.find_element(By.CSS_SELECTOR, ".product-gallery__carousel-item.is-selected img")
                            selected_image_url = selected_image_element.get_attribute("src")
                        except Exception as e:
                            print(f"Error finding selected image: {e}")
            
                    else:
                        selected_image_url = all_image_src[1]

                    # Append data
                    scraped_data.append({
                        "Handle": handle,
                        "Title": title,
                        "Variation":variation_name,
                        "Body (HTML)": relevant_table_html,
                        "Vendor": vendor,
                        "Type": breadcrumb_type,
                        "Tags": tags,
                                                    "Option1 Name": "Color",
                        "Option1 Value": option2_value,
                                                    "Option2 Name": "Size",

                        "Option2 Value": option1_value,
                        "Variant SKU": variant_sku,
                                                    "Variant Grams": " ",
                                        "Variant Inventory Tracker": "shopify",
            "Variant Inventory Qty": "50000",
                                        "Variant Inventory Policy": "deny",
                                        "Variant Fulfillment Service": "manual",
                        "Variant Price": variant_price,
                        "Variant Compare At Price": variant_compare_price,
                                        "Variant Requires Shipping": "TRUE",
                                            "Variant Taxable": "TRUE",
                                        "Variant Barcode": variant_barcode,
                                                                    "Variant Weight Unit":" ",
                                        "Gift Card": "FALSE",

                        "Weight": weight,
                        "SEO Title": title,
                        "Product description box = Product Details Field (product.metafields.custom.product_details_field)": product_description_box,
                        "Google Shopping / Condition": " ",
                                        "Status": "active",
                                                                    "Variant Description": variant_description,

                        "Coverage Area (product.metafields.custom.coverage_area)": coverage_area,
                        "pcsperbox (product.metafields.custom.pcsperbox)": pcs_per_box,
                        "Price Per Sq Ft (product.metafields.custom.price_per_sq_ft)": price_per_sq_ft_text,
                        "Image Src": filtered_images[idx] if idx < len(filtered_images) else "",
                        "Variant Image": selected_image_url,
                        "Image Position": image_positions[idx] if idx < len(image_positions) else None,
                        "Original Price": original_price,
                        "Surface Type (product.metafields.custom.surface_type)": surface_attribute,
                        "uom (product.metafields.custom.uom)": uom,
                    })
                print(f"Scraped product {count}: {option2_value}")
                count += 1

            except Exception as e:
                print(f"Error scraping product {product_url}: {e}")

    
    df = pd.DataFrame(scraped_data)
    df.to_excel("scraped_data.xlsx", index=False, engine='openpyxl')

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the Excel file
    output_file = os.path.join(output_dir, "scraped_data.xlsx")
    df.to_excel(output_file, index=False, engine='openpyxl')
    
    print(f"Scraped data saved to {output_file}")

    driver.quit()


# enter the brand urls here
brands = ["https://floorscenter.com/collections/daltile"]

start_page = 1
end_page = 20

scrape_data(brands, start_page, end_page)
