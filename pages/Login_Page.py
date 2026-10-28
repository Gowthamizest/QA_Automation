from pages.Base_Page import BasePage

class LoginPage(BasePage):

    USERNAME = "//input[@name='username']"
    PASSWORD = "//input[@name='password']"
    LOGIN_BTN = "//button[@type = 'submit']/span[text() = 'Log In']"

    def login_user(self, username, password):
        self.send_text(self.USERNAME, username)
        self.send_text(self.PASSWORD, password)
        self.click(self.LOGIN_BTN)