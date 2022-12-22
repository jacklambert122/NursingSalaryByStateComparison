# %%
###############################################################################
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import seaborn as sns
from scipy import stats

###############################################################################
# %% State Income tax helper functions

# Helper to convert from hourly to annually
def HourlyToAnnual(hourly) -> int:
    return hourly * 40 * 52

# Helper to get effective tax as a rate
def StateEffectiveTax(hourly, Bracket_dict) -> float:
    annual = HourlyToAnnual(hourly)
    return StateEffectiveTaxTotal(annual, Bracket_dict) / annual

# Recursively solve for total tax owed in $
def StateEffectiveTaxTotal(annual, Bracket_dict) -> float:

    if( annual == 0):
        return 0

    for (key, val) in Bracket_dict.items():
        [lower, upper] = val
        inRange = (lower < annual <= upper)
        if inRange:
            Total = (annual-lower) * (key/100)
            next = lower

    return Total + StateEffectiveTaxTotal(next, Bracket_dict)

# Create State Income Tax Bracket w/ Marginal Rates
def CreateStateBracket(rate_arr, salary_arr) -> dict:

    new_dict = {}
    i = 0
    for rate in rate_arr:
        new_dict[rate] = [salary_arr[i], salary_arr[i+1]]
        i+=1
    return new_dict

# Take diff in pct of state 1 relative to state 2
def CalcTaxDeltaPct(hrly, state1, state2, State_Brackets) -> float:
    return StateEffectiveTax(hrly, State_Brackets[state2]) - StateEffectiveTax(hrly, State_Brackets[state1])

###############################################################################
#%% Salary Delta Plot
# Meant to be a plot function for a delta in tax rate between two states vs income
# State 1 - State to compare
# State 2 - Considered state to take delta from
# State Brackets - Dict with state income tax info
# Plots two axis - one in % and one in $
def plotDeltaTax(hourly_start, hourly_end, state1, state2, State_Brackets, ax):

    salary = []
    Pct_Delta_Arr = []
    Tax_Delta_Arr = []
    i = 0
    for hrly in range(hourly_start, hourly_end):

        Tax1 = StateEffectiveTax(hrly, State_Brackets[state1])
        Tax2 = StateEffectiveTax(hrly, State_Brackets[state2])
        annual = HourlyToAnnual(hrly)
        Tax_Delta_Pct = (Tax1 - Tax2)
        salary.append(annual)
        Pct_Delta_Arr.append(Tax_Delta_Pct)
        Tax_Delta_Arr.append(annual*Tax_Delta_Pct)

        if (Tax_Delta_Pct < 0):
            i+=1
            label_str = str(state1) + " - " + str(state2)
    ax[0].plot(salary, Pct_Delta_Arr, '-*', label = label_str)
    ax[1].plot(salary, Tax_Delta_Arr, '-*')
    ax[0].plot(salary, [0 for i in salary], '--k')
    ax[1].plot(salary, [0 for i in salary], '--k')
    ax[0].title.set_text("Tax Diff. (%) vs Salary ($)")
    ax[1].title.set_text("Tax Diff. (Dollars) vs Salary (Dollars)")
    ax[0].grid(True)
    ax[1].grid(True)
    ax[0].set_xticklabels([])

    print( state1 + " equivalent tax to " + state2 + " at salary: ", (salary[i+1]+salary[i])/2 )


###############################################################################
# MAIN
###############################################################################
#%%
if __name__ == '__main__':
    # State nursing salary data
    CO_df = pd.read_csv('Datafiles/Colorado.csv')
    NJ_df = pd.read_csv('Datafiles/NewJersey.csv')
    NY_df = pd.read_csv('Datafiles/NewYork.csv')

    # Create Dictionary to loop and eleivate repative coding patterns 
    states = {"CO": CO_df, "NJ": NJ_df , "NY": NY_df}
    colors = ["black", "blue", "red"]

    # Cost of Living Index in order of states dict
    CL_Index = [105.2, 114.0, 135.7]

    # Create tax bracket based on percent and marginal tax rates
    NY_Bracket = CreateStateBracket([4, 4.5, 5.25, 5.9, 5.97, 6.33], [0, 8500, 11700, 13900, 21400, 80650, 215400])
    NJ_Bracket = CreateStateBracket([1.4, 1.75, 3.5, 5.25, 6.37], [0, 20000, 35000, 40000, 75000, 500000])
    CO_Bracket = CreateStateBracket([4.55], [0, 500000])

    States_Brackets = {"NY": NY_Bracket, "NJ": NJ_Bracket, "CO": CO_Bracket}

    ###############################################################################
    #%% Renaming
    hourly_suffix = ' Hourly Base'
    yoe_suffix = ' YoE'
    for (state, df) in states.items():
        new_hourly_str = state + hourly_suffix
        new_yoe_str = state + yoe_suffix
        new_df = df.rename(columns={'Hourly Base Pay (Diff not included)': new_hourly_str, 
                                    'Years of Experience': new_yoe_str})
        states[state] = new_df

    ###############################################################################
    #%% Parse based on limits to make sure data is cleaned
    min_hourly = 0
    max_hourly = 70
    min_yoe = 0
    max_yoe = 20

    i = 0
    for (state, df) in states.items():
        hourly_str = state + hourly_suffix
        yoe_str = state + yoe_suffix
        states[state] = df[ (min_hourly < df[hourly_str]) & (df[hourly_str] < max_hourly) &
                            (min_yoe < df[yoe_str]) & (df[yoe_str] < max_yoe ) ]
    
    ###############################################################################
    #%% Plot Tax diffence in % and $ 
    fig, ax = plt.subplots(2)
    plotDeltaTax(1, 70, "NY", "CO", States_Brackets, ax) # Would want reusable for implementing more states
    plotDeltaTax(1, 70, "NJ", "CO", States_Brackets, ax)
    fig.legend()
    plt.show()

    ###############################################################################
    #%% Fit Hourly pay vs YoE by State w/ Cost of Living Adj. and State Income tax 
    # Use Sklearn for practice
    from sklearn.linear_model import LinearRegression  
    num_plots = 3        
    fig, ax0 = plt.subplots(num_plots)
    fig, ax1 = plt.subplots(num_plots)
    i = 0
    for (state, df) in states.items():

        hourly_str = state + hourly_suffix
        yoe_str = state + yoe_suffix

        X = df[yoe_str]
        Y = df[hourly_str]
        Y_CL= df[hourly_str].copy(deep=True)
        Y_CL = Y_CL.map(lambda x: x * float(100)/CL_Index[i])
        Y_SI = df[hourly_str].copy(deep=True)
        Y_SI = Y_SI.map(lambda hrly: hrly * (1 + CalcTaxDeltaPct(hrly, state, "CO", States_Brackets)) )
        Y_SI = Y_SI * float(100)/CL_Index[i]

        # For fitting
        X = X.values.reshape(-1, 1)
        Y = Y.values.reshape(-1, 1)
        Y_CL = Y_CL.values.reshape(-1, 1)
        Y_SI = Y_SI.values.reshape(-1, 1)

        # Add for regression coeff
        regr = LinearRegression() 
        regr1 = LinearRegression() 
        regr2 = LinearRegression() 
        fit = regr.fit(X,Y)
        fit_CL = regr1.fit(X,Y_CL)
        fit_SI = regr2.fit(X,Y_SI)
        res = fit.predict(X)
        res_CL = fit_CL.predict(X)
        res_SI = fit_SI.predict(X)
            # Plot Each state with each level of adjustment
        ax0[0].plot(X, res,'-*', label = state)
        ax0[0].set_title("Linear Fit - Hourly Pay vs YoE")
        ax0[1].plot(X, res_CL,'-*', label = state)
        ax0[1].set_title("Hourly Pay (Cost of Living Adj.) vs YoE")
        ax0[2].plot(X, res_SI,'-*', label = state)
        ax0[2].set_title("Hourly Pay (CoL & Tax Adjusted) vs YoE")
        ax0[0].grid(True)
        ax0[1].grid(True)
        ax0[2].grid(True)
        ax0[0].set_xticklabels([])
        ax0[1].set_xticklabels([])
        ax0[0].legend()

        # Plot Each state ontop of themselves with each adjustment
        ax1[i].plot(X, res,'-', label = "No Adj")
        ax1[i].plot(X, res_CL,'-', label = "CoL Adj")
        ax1[i].plot(X, res_SI,'-', label = "CoL & Tax Adj")
        ax1[i].set_title(state)
        ax1[i].grid(True)
        ax1[0].legend()
        if i != num_plots-1:
            ax1[i].set_xticklabels([])

        i+=1

    plt.show()

    ###############################################################################
    #%% Plot Salary vs Effective Tax Rate
    salary = [ HourlyToAnnual(hrly) for hrly in range(1, 70)]
    plt.figure()
    for (state, bracket) in States_Brackets.items():
        Effec = [ StateEffectiveTax(hrly, bracket) for hrly in range(1, 70)]
        plt.plot(salary, Effec, '-*', label = state)
    plt.xlabel("Annual Salary ($)")
    plt.ylabel("Effective State Income Tax Rate (%)")
    plt.legend()
    plt.show()

    ###############################################################################
    # %% Histograms - (1 to 3 YoE)
    # Parse for pertinaent data to Kendra
    year_min = 1
    year_max = 3
    i = 0
    fig, ax = plt.subplots()
    for (state, df) in states.items():
        state_str = state + hourly_suffix
        yoe_str = state + yoe_suffix

        new_df = df.copy(deep=True)
        new_df = new_df[ (year_min < new_df[yoe_str]) & (new_df[yoe_str] < year_max ) ]
        sns.histplot(data = new_df, x=state_str, ax=ax, stat="density", linewidth=0, kde=True, label=state, color=colors[i])
        plt.axvline(np.mean(new_df[state_str]),  ls='--', lw=1, color=colors[i], label=(state + " mean") )
        plt.axvline(np.median(new_df[state_str]),  ls=':', lw=1, color=colors[i],  label=(state + " median") )
        i+=1
    title_str = "Hourly Pay (" + str(year_min) + " to " + str(year_max) + " YoE)"
    ax.set(title=title_str, xlabel="Hourly Pay")
    plt.legend() 
    plt.show()

    ###############################################################################
    # %% Histograms - (1 to 3 YoE) - Cost of Living Adj.
    i = 0
    fig, ax = plt.subplots()
    for (state, df) in states.items():
        state_str = state + hourly_suffix
        yoe_str = state + yoe_suffix

        df_CL = df.copy(deep=True)
        df_CL = df_CL[ (year_min < df_CL[yoe_str]) & (df_CL[yoe_str] < year_max ) ]
        df_CL[state_str] = df_CL[state_str].map(lambda x: x * float(100)/CL_Index[i])

        sns.histplot(data = df_CL, x=state_str, ax=ax, stat="density", linewidth=0, kde=True, label=state, color=colors[i])
        plt.axvline(np.mean(df_CL[state_str]),  ls='--', lw=1, color=colors[i], label=(state + " mean") )
        plt.axvline(np.median(df_CL[state_str]),  ls=':', lw=1, color=colors[i], label=(state + " median") )
        i+=1
    title_str = "Normalized Hourly Pay by CoL (" + str(year_min) + " to " + str(year_max) + " YoE)"
    ax.set(title=title_str , xlabel="Normilized Hourly Pay")
    plt.legend() 
    plt.show()

    ###############################################################################
    # %% Histograms - (1 to 3 YoE) - Cost of Living Adj. & State Income Tax Adj.
    i = 0
    fig, ax = plt.subplots()
    for (state, df) in states.items():
        state_str = state + hourly_suffix
        yoe_str = state + yoe_suffix
        
        df_SI = df.copy(deep=True)
        df_SI = df_SI[ (year_min < df_SI[yoe_str]) & (df_SI[yoe_str] < year_max ) ]
        df_SI[state_str] = df_SI[state_str].map(lambda hrly: hrly * (1 + CalcTaxDeltaPct(hrly, state, "CO", States_Brackets)) )
        df_SI[state_str] = df_SI[state_str].map(lambda x: x * float(100)/CL_Index[i])

        sns.histplot(data = df_SI, x=state_str, ax=ax, stat="density", linewidth=0, kde=True, label=state, color=colors[i])
        plt.axvline(np.mean(df_SI[state_str]),  ls='--', lw=1, color=colors[i], label=(state + " mean") )
        plt.axvline(np.median(df_SI[state_str]),  ls=':', lw=1, color=colors[i], label=(state + " median") )
        i+=1
    title_str = "Normalized Hourly Pay by CoL (" + str(year_min) + " to " + str(year_max) + " YoE)"
    ax.set(title=title_str , xlabel="Normilized Hourly Pay")
    plt.legend() 
    plt.show()

    ###############################################################################
    #%% Fit Hourly pay vs YoE by State                     
    fig, ax = plt.subplots()
    i = 0
    for (state, df) in states.items():

        hourly_str = state + hourly_suffix
        yoe_str = state + yoe_suffix

        X = df[yoe_str] 
        Y = df[hourly_str] 

        # Add for regression coeff
        X = sm.add_constant(X)
        model = sm.OLS(Y, X, missing='drop')
        result = model.fit()
        print(result.summary())

        #linear fit plots
        sm.graphics.plot_fit(result,1, vlines=False, ax=ax, color=colors[i])
        i+=1
    ax.set_title("Linear Fit")
    ax.set_ylabel("Hourly Pay")
    ax.set_xlabel("Years of Experience")
    plt.show()

    ###############################################################################
    #%% Fit Hourly pay vs YoE by State w/ Cost of Living Adj.                  
    fig, ax = plt.subplots()
    i = 0
    for (state, df) in states.items():

        hourly_str = state + hourly_suffix
        yoe_str = state + yoe_suffix

        X = df[yoe_str]
        Y = df[hourly_str].copy(deep=True)
        Y = Y * float(100)/CL_Index[i]

        # Add for regression coeff
        X = sm.add_constant(X)
        model = sm.OLS(Y, X, missing='drop')
        result = model.fit()
        #result.summary()

        #linear fit plots
        sm.graphics.plot_fit(result,1, vlines=False, ax=ax, color=colors[i])
        i+=1
    ax.set_title("Linear Fit - Cost of Living Adjusted")
    ax.set_ylabel("Hourly Pay")
    ax.set_xlabel("Years of Experience")
    plt.show()

    ###############################################################################
    #%% Fit Hourly pay vs YoE by State w/ Cost of Living Adj. & Cost of Living           
    fig, ax = plt.subplots()
    i = 0
    for (state, df) in states.items():

        hourly_str = state + hourly_suffix
        yoe_str = state + yoe_suffix

        X = df[yoe_str]
        Y = df[hourly_str].copy(deep=True)
        Y = Y.map(lambda hrly: hrly * (1 + CalcTaxDeltaPct(hrly, state, "CO", States_Brackets)) )
        Y = Y.map(lambda x: x * float(100)/CL_Index[i])

        # Add for regression coeff
        X = sm.add_constant(X)
        model = sm.OLS(Y, X, missing='drop')
        result = model.fit()
        #result.summary()

        #linear fit plots
        sm.graphics.plot_fit(result,1, vlines=False, ax=ax, color=colors[i])
        i+=1

    ax.set_title("Linear Fit - Cost of Living & State Income Tax Adjusted")
    ax.set_ylabel("Hourly Pay")
    ax.set_xlabel("Years of Experience")
    plt.show()
    ###############################################################################

