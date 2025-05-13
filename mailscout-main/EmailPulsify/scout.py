import smtplib
import dns.resolver
import random
import string
import time
from typing import List, Optional, Union, Dict
from unidecode import unidecode
from concurrent.futures import ThreadPoolExecutor, as_completed


class Scout:
    def __init__(
        self,
        check_variants: bool = True,
        check_prefixes: bool = True,
        check_catchall: bool = True,
        normalize: bool = True,
        num_threads: int = 5,
        num_bulk_threads: int = 3,
        smtp_timeout: int = 2
    ) -> None:
        self.check_variants = check_variants
        self.check_prefixes = check_prefixes
        self.check_catchall = check_catchall
        self.normalize = normalize
        self.num_threads = num_threads
        self.num_bulk_threads = num_bulk_threads
        self.smtp_timeout = smtp_timeout

    def check_smtp(self, email: str, port: int = 25) -> Dict[str, Union[str, int, float, bool]]:
        domain = email.split('@')[1]
        ver_ops = 0
        connections = 0
        catch_all_flag = False
        mx_record = ""
        start_time = time.time()

        try:
            records = dns.resolver.resolve(domain, 'MX')
            mx_hosts = [str(r.exchange).rstrip('.') for r in records]

            for mx in mx_hosts:
                try:
                    with smtplib.SMTP(mx, port, timeout=self.smtp_timeout) as server:
                        connections += 1
                        server.set_debuglevel(0)
                        server.ehlo("blu-harvest.com")
                        server.mail('noreply@blu-harvest.com')
                        ver_ops += 1
                        code, message = server.rcpt(email)
                        ver_ops += 1
                        mx_record = mx

                        if code == 250:
                            if self.check_catchall:
                                catch_all_flag = self.is_catch_all(domain, mx)
                            status = "risky" if catch_all_flag else "valid"
                            msg = "Catch-All" if catch_all_flag else f"{code} {message.decode()}"
                        else:
                            status = "invalid"
                            msg = f"{code} {message.decode()}"

                        time_exec = round(time.time() - start_time, 3)
                        return {
                            "email": email,
                            "status": status,
                            "catch_all": catch_all_flag,
                            "message": msg,
                            "user_name": email.split('@')[0].replace('.', ' ').title(),
                            "domain": domain,
                            "mx": mx_record,
                            "connections": connections,
                            "ver_ops": ver_ops,
                            "time_exec": time_exec
                        }
                except Exception:
                    connections += 1
                    continue

            time_exec = round(time.time() - start_time, 3)
            return {
                "email": email,
                "status": "invalid",
                "catch_all": False,
                "message": "SMTP failed for all MX records & ports",
                "user_name": email.split('@')[0].replace('.', ' ').title(),
                "domain": domain,
                "mx": "",
                "connections": connections,
                "ver_ops": ver_ops,
                "time_exec": time_exec
            }

        except Exception as e:
            time_exec = round(time.time() - start_time, 3)
            return {
                "email": email,
                "status": "invalid",
                "catch_all": False,
                "message": f"Rejected: {str(e)}",
                "user_name": email.split('@')[0].replace('.', ' ').title(),
                "domain": domain,
                "mx": "",
                "connections": connections,
                "ver_ops": ver_ops,
                "time_exec": time_exec
            }

    def is_catch_all(self, domain: str, mx_record: str) -> bool:
        fake_user = ''.join(random.choices(string.ascii_lowercase, k=12))
        fake_email = f"{fake_user}@{domain}"

        try:
            with smtplib.SMTP(mx_record, 25, timeout=self.smtp_timeout) as server:
                server.set_debuglevel(0)
                server.ehlo("blu-harvest.com")
                server.mail("noreply@blu-harvest.com")
                code, _ = server.rcpt(fake_email)
                return code == 250
        except Exception:
            return False

    def find_valid_emails(self, domain: str, names: Optional[Union[str, List[str], List[List[str]]]] = None) -> Dict[str, Union[str, int, float, None]]:
        email_variants = []
        generated_mails = []

        if self.check_variants and names:
            if isinstance(names, str):
                names = names.split(" ")
            if isinstance(names, list) and names and isinstance(names[0], list):
                for name_list in names:
                    name_list = self.split_list_data(name_list)
                    email_variants.extend(self.generate_email_variants(name_list, domain, normalize=self.normalize))
            else:
                names = self.split_list_data(names)
                email_variants = self.generate_email_variants(names, domain, normalize=self.normalize)

        if self.check_prefixes and not names:
            generated_mails = self.generate_prefixes(domain)

        all_emails = list(set(email_variants + generated_mails))

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            future_to_email = {executor.submit(self.check_smtp, email): email for email in all_emails}
            for future in as_completed(future_to_email):
                result = future.result()
                if result["status"] in ["valid", "risky"]:
                    for f in future_to_email:
                        f.cancel()
                    return result
                time.sleep(random.uniform(0.5, 1.2))

        return {
            "email": None,
            "status": "invalid",
            "catch_all": False,
            "message": "No valid email found",
            "user_name": "",
            "domain": domain,
            "mx": "",
            "connections": 0,
            "ver_ops": 0,
            "time_exec": 0.0
        }

    def find_valid_emails_bulk(self, email_data: List[Dict[str, Union[str, List[str]]]]) -> List[Dict[str, Union[str, List[str], Dict[str, Union[str, int, float, None]]]]]:
        def worker(data):
            domain = data.get("domain")
            names = data.get("names", [])
            valid_email = self.find_valid_emails(domain, names)
            return {
                "domain": domain,
                "names": names,
                "valid_email": valid_email
            }

        with ThreadPoolExecutor(max_workers=self.num_bulk_threads) as executor:
            futures = [executor.submit(worker, data) for data in email_data]
            return [future.result() for future in as_completed(futures)]

    def split_list_data(self, target):
        new_target = []
        for i in target:
            new_target.extend(i.split(" "))
        return new_target

    def generate_email_variants(self, names: List[str], domain: str, normalize: bool = True) -> List[str]:
        if normalize:
            names = [unidecode(n).lower().strip() for n in names if n]
        first, last = names[0], names[-1] if len(names) > 1 else ("", names[0])
        patterns = [
            f"{first}@{domain}",
            f"{first}{last}@{domain}",
            f"{first}.{last}@{domain}",
            f"{first}_{last}@{domain}",
            f"{last}.{first}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first[0]}.{last}@{domain}",
            f"{first}{last[0]}@{domain}",
            f"{first[0]}{last[0]}@{domain}",
            f"{last}{first}@{domain}",
            f"{last}@{domain}"
        ]
        return list(set(patterns))

    def generate_prefixes(self, domain: str) -> List[str]:
        prefixes = ['admin', 'contact', 'hello', 'team', 'support', 'info', 'mail']
        return [f"{prefix}@{domain}" for prefix in prefixes]
