import yaml

def YamlReader(keys=None):
    with open('config.yaml', 'r') as f:
        config = yaml.load(f, Loader=yaml.CLoader)
        if keys == None:
            return config
        else:
            for key in keys.split('.'):
                if key in config:
                    config = config[key]
                else:
                    config = ""
            return config
