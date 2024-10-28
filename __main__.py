from libs.scraper import Scraper


def main():
    
    scraper = Scraper()
    
    while True:
        
        option = input("1) Save groups\n2) Post in groups\n3) muti image\n 4 exit \nOption: ")
        if option == "1":
            keyword = input("Enter keyword: ")
            scraper.save_groups(keyword)
        elif option == "2":
            scraper.post_in_groups()
        elif option == "3":
            scraper.post_in_groupsx()
        elif option == "4":
             break
        else:
            print("Invalid option")


if __name__ == "__main__":
    main()