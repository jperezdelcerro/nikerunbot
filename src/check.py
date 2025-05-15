from main import NikeRunBot

def main():
    url = "https://www.nike.com.ar/run-crew-buenos-aires"
    bot = NikeRunBot(url, intervalo=0)  
    bot.escuchar_start()     
    bot.verificar_estado()   

if __name__ == "__main__":
    main()