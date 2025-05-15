from nikerunbot import NikeRunBot


def main():
    url = "https://www.nike.com.ar/run-crew-buenos-aires"

    bot = NikeRunBot(url, intervalo=300)  # cada 5 minutos
    bot.run()

if __name__ == "__main__":
    main()