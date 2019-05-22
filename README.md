# Castor Donkeycar

This repository contains configured Castor donkeycar.

# Training
```sh
python manage.py train --tub <data_directory> --model <model_name>
```

If you want to continue training of some specific model, define base model:
```sh
python manage.py train --tub <data_directory> --model <model_name> --base_model <base_model_name>
```
