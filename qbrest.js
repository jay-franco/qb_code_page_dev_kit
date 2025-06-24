class QbRest {
    constructor(realm, appToken) {
        this.realm = realm;
        this.appToken = appToken;
    }
    tempTokens = {}
    baseUrl = "https://api.quickbase.com/v1";


    async #getTempAuth(tableId) {
        if (tableId in this.tempTokens) return this.tempTokens[tableId]

        const response = await fetch(`${this.baseUrl}/auth/temporary/${tableId}`,
            {
                method: 'GET',
                mode: 'cors', // no-cors, *cors, same-origin
                credentials: 'include', // include, *same-origin, omit
                headers: {
                    'QB-Realm-Hostname': this.realm,
                    'QB-App-Token': this.appToken
                },
            });

        if (response?.ok) {
            const json = await response.json()
            this.tempTokens[tableId] = json.temporaryAuthorization;
            setTimeout(function () { delete this.tempTokens[tableId]; }, 1000 * 60 * 4);
            return this.tempTokens[tableId];
        } else {
            console.log(`HTTP Response Code: ${response?.status}`);
            return false;
        }

    }


    async qbaMakeRequest(method, endpoint, dbid, data = null, params = null) {
        const query = params ? this.parameterize(params) : "";
        const url = `${this.baseUrl}/${endpoint}${query}`;
        const opts = {
            method: method,
            headers: {
                'QB-Realm-Hostname': this.realm,
                'Content-Type': 'application/json',
                'Authorization': `QB-TEMP-TOKEN ${await this.#getTempAuth(dbid)}`
            },
        }

        if (data !== null) opts['body'] = JSON.stringify(data)

        const response = await fetch(url, opts);
        if (response?.ok) {
            const json = await response.json()
            return json;
        } else {
            console.log(`HTTP Response Code: ${response?.status}`);
            return false;
        }

    }


    async qbaGetReport(dbid, report) {
        const response = await this.qbaMakeRequest('POST', `reports/${report}/run`, dbid, null, { "tableId": dbid });
        if (!response) {
            console.log(`HTTP Response Code: ${response?.status}`);
            return false;
        }
        return response;
    }

    async qbaUpsert(dbid, fields) {
        const reqdata = {};
        reqdata.to = dbid;
        reqdata.data = fields;
        const response = await this.qbaMakeRequest('POST', 'records', dbid, reqdata);

        if (!response) {
            console.log(`HTTP Response Code: ${response?.status}`);
            return false;
        }
        return response;
    }

    async qbaQuery(dbid, fields, qry, sort = null) {
        const reqdata = {};
        reqdata.from = dbid;
        reqdata.select = fields;
        qry && (reqdata.where = qry);
        sort && (reqdata.sortBy = sort);

        const response = await this.qbaMakeRequest('POST', 'records/query', dbid, reqdata);
        if (!response) {
            console.log(`HTTP Response Code: ${response?.status}`);
            return false;
        }
        return response;
    }

    parameterize(paramObject) {
        return "?" + Object.keys(paramObject).map(key => key + '=' + paramObject[key]).join('&');
    }

    async preauthTable(tid) {
        this.#getTempAuth(tid)
    }

    async getUserXml() {
        const url = `https://${this.realm}/db/main?a=API_GetUserInfo&ticket=${this.appToken}`;
        const response = await fetch(url);
        if (!response) {
            console.log(`HTTP Response Code: ${response?.status}`);
            return false;
        }
        return response.text();
    }

}