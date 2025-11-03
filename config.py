import yaml

class Config():
    def __init__(self, config_file_path='config.yaml'):
        self.config_file_path = config_file_path
        self.deck_name = 'None'
        self.confidence_level = 0.6
        self.delay_between_screen_checks = 0
        self.web_page_theme = 'system'
        self.update_config()

    def update_config(self):
        with open(self.config_file_path, 'r') as file:
            data = yaml.safe_load(file)
            print(f"Config: {data}")


        # deck_name
        try:
            if str(data['deck_name']) == 'None':
                self.deck_name = None
            else:
                self.deck_name = str(data['deck_name'])
        except:
            self.deck_name = None


        # confidence_level
        try:
            self.confidence_level = float(data['confidence_level'])
        except:
            self.confidence_level = 0.6


        # delay_between_screen_checks
        try:
            self.delay_between_screen_checks = float(data['delay_between_screen_checks'])
        except:
            self.delay_between_screen_checks = 0


        # web_page_theme
        try:
            if str(data['web_page_theme']).lower() == 'system' or str(data['web_page_theme']).lower() == 'dark' or str(data['web_page_theme']).lower() == 'light':
                self.web_page_theme = str(data['web_page_theme']).lower()
            else:
                self.web_page_theme = 'system'
        except:
            self.web_page_theme = 'system'

if __name__ == "__main__":
    CONFIG = Config() 