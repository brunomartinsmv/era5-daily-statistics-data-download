# Config

Configuration examples for local ERA5/CDS access.

## Files

- `cdsapirc.example`: template for the CDS API credentials file.

## Usage

Copy the template to your home directory and replace the placeholder values with
your CDS UID and API key:

```bash
cp config/cdsapirc.example ~/.cdsapirc
```

Never commit a real `.cdsapirc` file or API key to this repository.
