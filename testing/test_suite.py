from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

class TestSuite():
  def setup_method(self, method):
    self.driver = webdriver.Chrome()
    self.driver.implicitly_wait(10)  # Implicit wait for elements
    self.vars = {}
  
  def teardown_method(self, method):
    self.driver.quit()
  
  def test_navigation(self):
    self.driver.get("http://127.0.0.1:5000/")
    self.driver.set_window_size(1454, 866)
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Home"))).click()
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "About"))).click()
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".nav-link:nth-child(3)"))).click()
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Recommend me songs"))).click()
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Metronome"))).click()
  
  def test_recommend(self):
    self.driver.get("http://127.0.0.1:5000/")
    wait = WebDriverWait(self.driver, 10)  # Explicit Waits

    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Recommend me songs"))).click()
    wait.until(EC.presence_of_element_located((By.ID, "artist"))).click()
    self.driver.find_element(By.ID, "artist").send_keys("aes")

    # Handling StaleElementReferenceException
    for _ in range(3):  # Retry up to 3 times
      try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".suggestion-item:nth-child(3)"))).click()
        break  # Exit loop if successful
      except StaleElementReferenceException:
        continue  # Retry finding the element

    alpha_slider = wait.until(EC.presence_of_element_located((By.ID, "alpha")))
    actions = ActionChains(self.driver)
    actions.move_to_element(alpha_slider).click_and_hold().release().perform()
    alpha_slider.send_keys("1")

    wait.until(EC.element_to_be_clickable((By.ID, "generate-btn"))).click()

    # Verifying dropdown selection
    genre_filter = wait.until(EC.presence_of_element_located((By.ID, "genre-filter")))
    genre_filter.click()
    genre_filter.find_element(By.XPATH, "//option[. = 'All']").click()

    # Handling dynamic dropdowns (StaleElementReferenceException)
    mode_filter = wait.until(EC.presence_of_element_located((By.ID, "mode-filter")))
    for _ in range(3):  
      try:
        mode_filter.click()
        mode_filter.find_element(By.XPATH, "//option[. = 'Major']").click()
        break
      except StaleElementReferenceException:
        continue

    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".fa"))).click()

    # Verifying expected values
    assert genre_filter.get_attribute("value") == "all"
    assert mode_filter.get_attribute("value") == "Major"

    print("Test passed successfully!")
  
  def test_metronome(self):
    self.driver.get("http://127.0.0.1:5000/")
    self.driver.set_window_size(974, 1032)
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Metronome"))).click()
    
    slider = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".slider")))
    slider.send_keys("75")
    
    tempo_value = self.driver.find_element(By.CSS_SELECTOR, ".slider").get_attribute("value")
    assert tempo_value == "150", f"Expected 150, but got {tempo_value}"
    
    self.driver.find_element(By.CSS_SELECTOR, ".increase-tempo").click()
    self.driver.find_element(By.CSS_SELECTOR, ".decrease-tempo").click()
    
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".start-stop"))).click()
